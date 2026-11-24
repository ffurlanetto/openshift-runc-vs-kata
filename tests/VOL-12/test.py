"""VOL-12 : un pod compromis (privilégié) atteint-il les volumes des AUTRES pods du nœud ?

Victime : pod runc avec une PVC (backend local), qui y écrit un fichier marqueur au nom unique.
Attaquant (runtime du run) : pod privilégié, root, SANS hostPath ni namespace de l'hôte, sur le même nœud.
Il monte EN LECTURE SEULE (ro,norecovery) chaque périphérique bloc visible et cherche le fichier marqueur
par son nom. Il relève aussi les montages et répertoires kubelet visibles. Aucune écriture.

runc : les périphériques du nœud sont visibles, le volume de la victime est attendu accessible.
Kata : seuls les périphériques de la VM sont visibles, le volume de la victime est attendu inaccessible.
"""

import base64
import secrets as pysecrets

from kvr import storage

META = {"intrusive": "pod privilégié qui monte les disques bloc du nœud en lecture seule",
        "id": "VOL-12", "category": "VOL", "aspect": "SEC", "priority": "P1",
        "title": "Pod compromis : accès aux volumes des autres pods", "runs": 2, "warmup": False,
        "params": {"storage_class": ""}}

SCRIPT = r"""
for dev in $(ls /sys/class/block); do
  [ -b /dev/$dev ] || mknod /dev/$dev b $(tr ':' ' ' < /sys/class/block/$dev/dev) 2>/dev/null
  mkdir -p /mnt/$dev
  if mount -o ro,norecovery,nouuid /dev/$dev /mnt/$dev 2>/dev/null || mount -o ro /dev/$dev /mnt/$dev 2>/dev/null; then
    echo "MOUNTED $dev"
    if timeout 180 find /mnt/$dev -xdev -name "$MARKER" -type f 2>/dev/null | grep -q .; then echo "FOUND $dev"; fi
    umount /mnt/$dev 2>/dev/null
  fi
done
echo "DEVICES $(ls /sys/class/block | tr '\n' ' ')"
echo "KUBELET_MOUNTS $(grep -c kubelet /proc/mounts)"
"""


def run(ctx):
    sc = storage.storage_class(ctx, "local")
    marker = "kvr-marqueur-vol-" + pysecrets.token_hex(8)
    ctx.apply_template("pvc-pod.yaml.j2", pvc="victim-data", storage_class=sc["name"], name="victim", rc="runc")
    ctx.wait("pod/victim", timeout_s=300)
    rc, _, err = ctx.exec("victim", ["sh", "-c", f"echo confidentiel > /data/{marker} && sync"])
    assert rc == 0, f"écriture du marqueur impossible : {err.strip()[:200]}"
    node = ctx.get("pod/victim")["spec"]["nodeName"]

    ctx.grant_scc("privileged")
    ctx.apply_template("host-reader-pod.yaml.j2", name="attacker", node_name=node)
    ctx.wait("pod/attacker", timeout_s=240)
    b64 = base64.b64encode(SCRIPT.replace("$MARKER", marker).encode()).decode()
    rc, out, err = ctx.exec("attacker", ["sh", "-c", f"echo {b64} | base64 -d | sh"], timeout_s=1200)
    lines = out.splitlines()
    mounted = [l.split()[1] for l in lines if l.startswith("MOUNTED ")]
    found = [l.split()[1] for l in lines if l.startswith("FOUND ")]
    devices = next((l[len("DEVICES "):] for l in lines if l.startswith("DEVICES ")), "")
    ctx.evidence("attack.txt", f"rc={rc}\nbackend={sc}\nmontés={mounted}\ntrouvé sur={found}\n"
                               f"disques={devices}\n{next((l for l in lines if l.startswith('KUBELET')), '')}\n{err[-500:]}")
    ctx.metric("victim_volume_reached", int(bool(found)), "bool", "lower")
    ctx.metric("block_devices_mountable", len(mounted), "count", "lower")
    ctx.observe(f"attaquant {ctx.runtime} privilégié : {len(mounted)} périphérique(s) monté(s) ({', '.join(mounted) or 'aucun'}) ; "
                f"volume de la victime ({sc['name']}) {'ATTEINT sur ' + ', '.join(found) if found else 'non atteint'}")
    expected = ctx.runtime == "runc"
    return "PASS" if bool(found) == expected else "FAIL"
