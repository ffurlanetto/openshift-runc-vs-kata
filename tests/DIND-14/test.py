"""DIND-14 : étape de pipeline malveillante dans un job V1 (dind privilégié).

Depuis un conteneur lancé par le dind interne avec --privileged (ce qu'une PR malveillante peut faire),
on tente de monter EN LECTURE SEULE (ro,norecovery) chaque partition visible (si la partition est déjà
montée par le nœud : montage partageant le superbloc puis rebascule immédiate en lecture seule), et on cherche un
répertoire kubelet de CE pod (…/kubelet/pods/<uid du pod>), qui n'existe que sur le disque du nœud.
Critère indépendant de la distribution (RHCOS/ostree, Ubuntu…).
Aucune écriture, aucun exploit : on démontre seulement l'accès au système de fichiers du nœud.

runc : attendu = disque du nœud monté (nœud compromis). kata : attendu = seuls les disques de la VM.
"""

import base64

from kvr import dind
from kvr.context import NotSupported

META = {"id": "DIND-14", "category": "DIND", "aspect": "SEC", "priority": "P1",
        "title": "Étape malveillante : accès au disque du nœud", "variants": ["V1-dind-privileged", "V5-dind-privileged-memstore"], "runs": 1,
        "warmup": False}

SCRIPT = r"""
for dev in $(ls /sys/class/block); do
  [ -b /dev/$dev ] || mknod /dev/$dev b $(tr ':' ' ' < /sys/class/block/$dev/dev) 2>/dev/null
  mkdir -p /mnt/$dev
  mode=ro
  if ! { mount -o ro,norecovery,nouuid /dev/$dev /mnt/$dev 2>/dev/null || mount -o ro /dev/$dev /mnt/$dev 2>/dev/null; }; then
    # Partition déjà montée par le nœud (ex. racine XFS) : le noyau refuse un 2e montage ro du même superbloc.
    # Un attaquant monte alors sans option (superbloc partagé) ; on rebascule aussitôt la vue en lecture seule.
    if mount /dev/$dev /mnt/$dev 2>/dev/null; then
      mount -o remount,bind,ro /mnt/$dev 2>/dev/null; mode=partage
    else
      continue
    fi
  fi
  if true; then
    hit=
    for c in /mnt/$dev/var/lib/kubelet /mnt/$dev/lib/kubelet /mnt/$dev/ostree/deploy/*/var/lib/kubelet; do
      [ -d "$c/pods/$POD_UID" ] && hit=1
    done
    [ -z "$hit" ] && timeout 120 find /mnt/$dev -maxdepth 9 \( -path "*/ostree/repo" -o -path "*/containers/storage" \) -prune \
      -o -type d -path "*kubelet/pods/$POD_UID" -print 2>/dev/null | grep -q . && hit=1
    if [ -n "$hit" ]; then
      echo "NODEFS $dev"
    fi
    echo "MOUNTED $dev $mode"
    umount /mnt/$dev 2>/dev/null
  fi
done
echo "DEVICES $(ls /sys/class/block | tr '\n' ' ')"
"""


def run(ctx):
    dind.deploy(ctx)
    dind.wait_engine(ctx)
    pod_uid = ctx.get(f"pod/{dind.POD}")["metadata"]["uid"]
    image = ctx.images["ubi"]
    b64 = base64.b64encode(SCRIPT.replace("$POD_UID", pod_uid).encode()).decode()
    rc, out, err = dind.sh(ctx, f"docker run --rm --privileged {image} sh -c 'echo {b64} | base64 -d | sh'",
                           timeout_s=900)
    if rc != 0:
        ctx.evidence("escape-attempt.txt", f"rc={rc}\n{(out + err)[-1500:]}")
        raise NotSupported(f"conteneur imbriqué non lancé (rc={rc}) : scénario non exécutable ; "
                           f"{(out + err).strip().splitlines()[-1][:200] if (out + err).strip() else ''}")
    lines = out.splitlines()
    mounted = [l.split()[1] for l in lines if l.startswith("MOUNTED ")]
    modes = {l.split()[1]: (l.split() + ["?", "?", "?"])[2] for l in lines if l.startswith("MOUNTED ")}
    node_devs = [l.split()[1] for l in lines if l.startswith("NODEFS ")]
    devices = next((l[len("DEVICES "):] for l in lines if l.startswith("DEVICES ")), "")
    # La preuve ne conserve pas d'identifiant : seulement le résultat de la comparaison.
    ctx.evidence("escape-attempt.txt", f"rc={rc}\nmontés (mode)={modes}\ndisques={devices}\n"
                                       f"répertoire kubelet du pod trouvé sur : {node_devs}\n{err[-500:]}")
    node_fs = bool(node_devs)
    ctx.metric("node_rootfs_mounted", int(node_fs), "bool", "lower")
    ctx.metric("block_devices_mountable", len(mounted), "count", "lower")
    ctx.observe(f"{ctx.runtime} : {len(mounted)} partition(s) montée(s) depuis le conteneur imbriqué ; "
                f"système de fichiers du NŒUD {'ACCESSIBLE' if node_fs else 'non accessible'}"
                f"{' (via ' + ', '.join(f'{d}:{modes[d]}' for d in node_devs) + ')' if node_fs else ''}")
    expected = ctx.runtime == "runc"
    return "PASS" if node_fs == expected else "FAIL"
