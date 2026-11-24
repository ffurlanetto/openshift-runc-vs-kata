"""SEC-05 : un `hostPath` accordé est-il un accès au nœud, même avec Kata ?

Pods dans le runtime du run, root mais NON privilégiés, avec un montage hôte :
- /shared : répertoire dédié du nœud /var/tmp/kvr-sec05-<jeton>, en écriture. Deux pods : l'un avec le
  contexte SELinux par défaut du cluster (le noyau du nœud peut refuser, indépendamment de Kata), l'autre avec
  `spc_t` (ce que l'admission SCC « privileged » permet à qui reçoit un hostPath) ;
- /hostroot : la racine du nœud, en LECTURE SEULE, dans un pod séparé (`spc_t`) : on teste l'accès, sans lire
  de contenu. Un échec de démarrage de ce pod est constaté, sans faire échouer le test.
Une sonde runc sur le même nœud dépose un fichier, le pod le lit et en écrit un autre, la sonde le relit
(propriétaire vu côté nœud). Le pod racine vérifie s'il pourrait lire des fichiers sensibles du nœud
(`/etc/shadow`, configuration du kubelet) : test d'accès uniquement, contenu jamais lu.

Attendu (plan) : accès dans les deux runtimes. Avec Kata, le montage passe par virtio-fs : Kata ne protège
pas un hostPath accordé. Seule l'admission (SCC, Kyverno) l'empêche. PASS = accès complet (lecture, écriture vue du nœud) avec spc_t
et nœud remis en l'état ; le résultat avec le SELinux par défaut est relevé à part.
"""

from kvr import escape

META = {"intrusive": "pod avec hostPath en écriture sur un répertoire dédié du nœud et la racine du nœud en lecture "
                     "(accès testé, aucun contenu lu)",
        "id": "SEC-05", "category": "SEC", "aspect": "SEC", "priority": "P1",
        "title": "hostPath : accès au nœud malgré Kata ?", "runs": 2, "warmup": False}

POD_SIDE = r"""
T=$1; V=$2
echo "READ $( [ "$(cat /shared/from-node 2>/dev/null)" = "kvr-node-$T" ] && echo oui || echo non)"
echo "WRITE $(echo kvr-pod-$T > /shared/from-pod-$V 2>/dev/null && echo oui || echo non)"
echo "FSTYPE $(awk '$2=="/shared"{print $3}' /proc/mounts)"
echo "LABEL $(cat /proc/self/attr/current 2>/dev/null | tr -d '\0')"
"""

ROOT_SIDE = r"""
T=$1
echo "FSTYPE $(awk '$2=="/hostroot"{print $3}' /proc/mounts)"
for f in /hostroot/etc/shadow /hostroot/var/lib/kubelet/config.yaml /hostroot/etc/kubernetes/kubelet.conf; do
  [ -e "$f" ] || { echo "SENSITIVE $(basename $f) absent"; continue; }
  echo "SENSITIVE $(basename $f) $( head -c1 "$f" >/dev/null 2>&1 && echo lisible || echo refusé)"
done
echo "ROOTWRITE $(touch /hostroot/var/tmp/kvr-sec05-$T-ro 2>/dev/null && echo oui || echo non)"
"""

NODE_PREP = r"""T=$1; mkdir -p /nodetmp/kvr-sec05-$T && echo kvr-node-$T > /nodetmp/kvr-sec05-$T/from-node && echo PREP ok"""
NODE_CHECK = r"""
T=$1; d=/nodetmp/kvr-sec05-$T
for v in defaut spc; do
  echo "SEEN_$v $( [ "$(cat $d/from-pod-$v 2>/dev/null)" = "kvr-pod-$T" ] && echo oui || echo non)"
  echo "OWNER_$v $(stat -c '%u:%g' $d/from-pod-$v 2>/dev/null || echo -)"
done
rm -rf $d /nodetmp/kvr-sec05-$T-ro
echo "LEFT $(ls -d /nodetmp/kvr-sec05-$T* 2>/dev/null | wc -l)"
"""


def kv(out: str, key: str) -> str:
    return next((l.split(maxsplit=1)[1] if " " in l else "" for l in out.splitlines() if l.startswith(key + " ")), "?")


def run(ctx):
    tok = escape.token()
    ctx.grant_scc("privileged")
    probe = escape.deploy(ctx, "nodecheck", rc="runc", privileged=True, run_as_user=0,
                          host_paths=[{"path": "/var/tmp", "mount": "/nodetmp", "ro": False}])
    node = probe["spec"]["nodeName"]
    rc, out, err = escape.run_sh(ctx, "nodecheck", NODE_PREP, tok, timeout_s=60)
    assert "PREP ok" in out, f"préparation côté nœud en échec : {err[-200:]}"
    shared = [{"path": f"/var/tmp/kvr-sec05-{tok}", "mount": "/shared", "ro": False}]
    pod_out, start_notes = {}, {}
    root_out, root_note, node_out = "", "", ""
    try:
        start_notes = {}
        for variant, se in (("defaut", None), ("spc", "spc_t")):
            try:
                escape.deploy(ctx, f"hp-{variant}", run_as_user=0, allow_pe=False, node_name=node, se_type=se,
                              timeout_s=150, host_paths=shared)
            except Exception as e:  # ex. Kata + SELinux par défaut : création du conteneur refusée (EACCES)
                start_notes[variant] = "pod non démarré"
                pod_out[variant] = ""
                ctx.evidence(f"start-{variant}.txt", str(e)[-1500:])
                continue
            rc, pod_out[variant], err = escape.run_sh(ctx, f"hp-{variant}", POD_SIDE, tok, variant, timeout_s=120)
        try:
            escape.deploy(ctx, "hostroot", run_as_user=0, allow_pe=False, node_name=node, se_type="spc_t",
                          timeout_s=150, host_paths=[{"path": "/", "mount": "/hostroot", "ro": True}])
            rc, root_out, err = escape.run_sh(ctx, "hostroot", ROOT_SIDE, tok, timeout_s=120)
        except Exception as e:  # démarrage refusé ou trop long : constat, pas un échec du test
            root_note = f"pod hostPath « / » non démarré : {str(e)[-160:]}"
        ctx.evidence("pod-side.txt", "\n".join(f"== {v}\n{o}" for v, o in pod_out.items()) +
                     f"\n== racine\n{root_out}\n{root_note}")
    finally:
        rc, node_out, err = escape.run_sh(ctx, "nodecheck", NODE_CHECK, tok, timeout_s=60)
        ctx.evidence("node-side.txt", f"rc={rc}\n{node_out}\n{err[-500:]}")
    left = kv(node_out, "LEFT")

    def access(v):
        o = pod_out.get(v, "")
        return kv(o, "READ") == "oui", kv(o, "WRITE") == "oui", kv(node_out, f"SEEN_{v}") == "oui"

    d_read, d_write, d_seen = access("defaut")
    read, write, seen = access("spc")
    sensitive = [l.split(maxsplit=2)[1:] for l in root_out.splitlines() if l.startswith("SENSITIVE ")]
    readable = [n for n, st in sensitive if st == "lisible"]
    ctx.metric("hostpath_read", int(read), "bool", "lower")
    ctx.metric("hostpath_write_seen_on_node", int(seen), "bool", "lower")
    ctx.metric("hostpath_access_default_selinux", int(d_read and d_write and d_seen), "bool", "lower")
    ctx.metric("hostpath_default_selinux_pod_started", int("defaut" not in start_notes), "bool", "lower")
    ctx.metric("node_sensitive_files_readable", len(readable), "count", "lower")
    ctx.observe(f"{ctx.runtime} : hostPath avec spc_t : lu={'oui' if read else 'non'}, écriture vue par le nœud="
                f"{'oui' if seen else 'non'} (propriétaire côté nœud {kv(node_out, 'OWNER_spc')}"
                f"{', ' + start_notes['spc'] if 'spc' in start_notes else ''}) ; avec le SELinux "
                f"par défaut ({kv(pod_out.get('defaut', ''), 'LABEL')}) : "
                + (f"{start_notes['defaut']} ; " if 'defaut' in start_notes else
                   f"lu={'oui' if d_read else 'non'}, écrit={'oui' if d_write else 'non'} ; ")
                + f"type de montage {kv(pod_out.get('spc', ''), 'FSTYPE')} ; "
                + (root_note or f"racine du nœud en lecture seule : fichiers sensibles lisibles {readable or 'aucun'}, "
                                f"écriture refusée={'oui' if kv(root_out, 'ROOTWRITE') == 'non' else 'NON'}")
                + f" ; résidus : {left}")
    if left != "0":
        return "FAIL"
    return "PASS" if (read and write and seen) else "FAIL"
