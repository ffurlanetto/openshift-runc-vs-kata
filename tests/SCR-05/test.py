"""SCR-05 : un pod compromis lit-il les secrets des AUTRES pods du même nœud ?

Attaquant (runtime du run) : pod privilégié avec `hostPath: /var/lib/kubelet/pods` en lecture seule,
mauvaise configuration réaliste (agents de sauvegarde, de supervision…). Victimes : un pod runc et un pod
Kata, chacun avec un secret marqueur, sur le même nœud. L'attaquant tente de lire le secret de chaque
victime, par l'UID de la victime uniquement (aucun autre pod du nœud n'est lu).

Le secret d'une victime est dans le tmpfs du kubelet, sur le nœud, quel que soit le runtime de la victime.
La question est donc ce que l'ATTAQUANT voit à travers son hostPath : avec runc, le répertoire du nœud et
ses sous-montages ; avec Kata, le partage virtio-fs de ce répertoire (sous-montages tmpfs inclus ou non).
"""

import secrets as pysecrets

from kvr import secrets
from kvr.context import Blocked

META = {"intrusive": "pod avec hostPath sur le répertoire du kubelet : recherche des secrets d'autres pods (pods de test uniquement)",
        "id": "SCR-05", "category": "SCR", "aspect": "SEC", "priority": "P1",
        "title": "Pod compromis : collecte des secrets des autres pods du nœud", "runs": 2, "warmup": False}


def run(ctx):
    if not ctx.kata_runtime_class:
        raise Blocked("RuntimeClass Kata inconnue : victime Kata impossible")
    victims, markers = {}, {}
    node = None
    for vrt, rc in (("kata", ctx.kata_runtime_class), ("runc", "runc")):
        markers[vrt] = f"kvr-marqueur-{vrt}-" + pysecrets.token_hex(8)
        secrets.create_secret(ctx, f"victim-{vrt}", {"value": markers[vrt].encode()})
        ctx.apply_template("secret-pod.yaml.j2", name=f"victim-{vrt}", rc=rc, node_name=node,
                           secret_volumes=[{"name": "s", "secret": f"victim-{vrt}"}])
        ctx.wait(f"pod/victim-{vrt}", timeout_s=240)
        pod = ctx.get(f"pod/victim-{vrt}")
        node = node or pod["spec"]["nodeName"]
        victims[vrt] = pod["metadata"]["uid"]

    ctx.grant_scc("privileged")
    ctx.apply_template("host-reader-pod.yaml.j2", name="attacker", node_name=node,
                       host_path="/var/lib/kubelet/pods")
    ctx.wait("pod/attacker", timeout_s=240)
    found, details = {}, {}
    for vrt, uid in victims.items():
        path = f"/host/{uid}/volumes/kubernetes.io~secret/s/value"
        rc, out, err = ctx.exec("attacker", ["sh", "-c", f"ls -d /host/{uid} >/dev/null 2>&1 && echo dir=1 || echo dir=0; "
                                                         f"cat {path} 2>&1 | head -c 200"])
        found[vrt] = markers[vrt] in out
        details[vrt] = {"pod_dir_visible": "dir=1" in out,
                        "read": found[vrt], "error": "" if found[vrt] else out.replace(markers[vrt], "")[:200]}
        ctx.metric(f"stolen_from_{vrt}", int(found[vrt]), "bool", "lower")
    _, mounts, _ = ctx.exec("attacker", ["sh", "-c", "grep -c ' /host' /proc/mounts; "
                                         "awk '$2 == \"/host\" {print $3}' /proc/mounts"])
    ctx.evidence("attack.json", {"attacker_runtime": ctx.runtime, "victims": details,
                                 "host_mounts": mounts.split()})
    ctx.observe(f"attaquant {ctx.runtime} (hostPath kubelet en lecture seule) : secret de la victime runc "
                f"{'VOLÉ' if found['runc'] else 'non lu'}, de la victime Kata {'VOLÉ' if found['kata'] else 'non lu'} ; "
                f"répertoires des pods visibles : runc={details['runc']['pod_dir_visible']}, "
                f"kata={details['kata']['pod_dir_visible']} ; montages sous /host : {mounts.split()[0] if mounts.split() else '?'}")
    expected = ctx.runtime == "runc"   # plan : attaquant runc lit tout, attaquant Kata ne lit rien
    return "PASS" if found["runc"] == expected and found["kata"] == expected else "FAIL"
