"""SEC-05 : un `hostPath` accordé est-il un accès au nœud, même avec Kata ?

Pod « hostpath » dans le runtime du run, root mais NON privilégié, avec deux montages hôte :
- /shared  : répertoire dédié du nœud /var/tmp/kvr-sec05-<jeton>, en écriture ;
- /hostroot : la racine du nœud, en LECTURE SEULE (on teste l'accès, on ne lit aucun contenu).
Une sonde runc sur le même nœud dépose un fichier, le pod le lit et en écrit un autre, la sonde le relit
(propriétaire vu côté nœud). Le pod vérifie ensuite s'il pourrait lire des fichiers sensibles du nœud
(`/etc/shadow`, configuration du kubelet) : test d'accès uniquement, contenu jamais lu.

Attendu (plan) : accès dans les deux runtimes. Avec Kata, le montage passe par virtio-fs : Kata ne protège
pas un hostPath accordé. Seule l'admission (SCC, Kyverno) l'empêche. PASS = constat conforme à l'attendu.
"""

from kvr import escape

META = {"intrusive": "pod avec hostPath en écriture sur un répertoire dédié du nœud et la racine du nœud en lecture "
                     "(accès testé, aucun contenu lu)",
        "id": "SEC-05", "category": "SEC", "aspect": "SEC", "priority": "P1",
        "title": "hostPath : accès au nœud malgré Kata ?", "runs": 2, "warmup": False}

POD_SIDE = r"""
T=$1
echo "READ $( [ "$(cat /shared/from-node 2>/dev/null)" = "kvr-node-$T" ] && echo oui || echo non)"
echo "WRITE $(echo kvr-pod-$T > /shared/from-pod 2>/dev/null && echo oui || echo non)"
echo "FSTYPE $(awk '$2=="/shared"{print $3}' /proc/mounts) $(awk '$2=="/hostroot"{print $3}' /proc/mounts)"
for f in /hostroot/etc/shadow /hostroot/var/lib/kubelet/config.yaml /hostroot/etc/kubernetes/kubelet.conf; do
  [ -e "$f" ] || { echo "SENSITIVE $(basename $f) absent"; continue; }
  echo "SENSITIVE $(basename $f) $( head -c1 "$f" >/dev/null 2>&1 && echo lisible || echo refusé)"
done
echo "ROOTWRITE $(touch /hostroot/var/tmp/kvr-sec05-$T-ro 2>/dev/null && echo oui || echo non)"
"""

NODE_PREP = r"""T=$1; mkdir -p /nodetmp/kvr-sec05-$T && echo kvr-node-$T > /nodetmp/kvr-sec05-$T/from-node && echo PREP ok"""
NODE_CHECK = r"""
T=$1; f=/nodetmp/kvr-sec05-$T/from-pod
echo "SEEN $( [ "$(cat $f 2>/dev/null)" = "kvr-pod-$T" ] && echo oui || echo non)"
echo "OWNER $(stat -c '%u:%g' $f 2>/dev/null || echo -)"
rm -rf /nodetmp/kvr-sec05-$T /nodetmp/kvr-sec05-$T-ro
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
    left, pod_out, node_out = "?", "", ""
    try:
        escape.deploy(ctx, "hostpath", run_as_user=0, allow_pe=False, node_name=node,
                      host_paths=[{"path": f"/var/tmp/kvr-sec05-{tok}", "mount": "/shared", "ro": False},
                                  {"path": "/", "mount": "/hostroot", "ro": True}])
        rc, pod_out, err = escape.run_sh(ctx, "hostpath", POD_SIDE, tok, timeout_s=120)
        ctx.evidence("pod-side.txt", f"rc={rc}\n{pod_out}\n{err[-500:]}")
    finally:
        rc, node_out, err = escape.run_sh(ctx, "nodecheck", NODE_CHECK, tok, timeout_s=60)
        ctx.evidence("node-side.txt", f"rc={rc}\n{node_out}\n{err[-500:]}")
        left = kv(node_out, "LEFT")

    read, write, seen = kv(pod_out, "READ") == "oui", kv(pod_out, "WRITE") == "oui", kv(node_out, "SEEN") == "oui"
    sensitive = [l.split(maxsplit=2)[1:] for l in pod_out.splitlines() if l.startswith("SENSITIVE ")]
    readable = [n for n, s in sensitive if s == "lisible"]
    ctx.metric("hostpath_read", int(read), "bool", "lower")
    ctx.metric("hostpath_write_seen_on_node", int(seen), "bool", "lower")
    ctx.metric("node_sensitive_files_readable", len(readable), "count", "lower")
    ctx.observe(f"{ctx.runtime} : hostPath lu={'oui' if read else 'non'}, écriture vue par le nœud={'oui' if seen else 'non'} "
                f"(propriétaire côté nœud {kv(node_out, 'OWNER')}) ; types de montage {kv(pod_out, 'FSTYPE')} ; "
                f"fichiers sensibles du nœud lisibles via hostPath / : {readable or 'aucun'} ; "
                f"écriture sur / monté en lecture seule : {kv(pod_out, 'ROOTWRITE')} ; résidus : {left}")
    if left not in ("0",):
        return "FAIL"
    return "PASS" if (read and write and seen) else "FAIL"
