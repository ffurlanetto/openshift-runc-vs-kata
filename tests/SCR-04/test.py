"""SCR-04 : où vit un secret, et l'administrateur du nœud peut-il le lire ?

Un pod « victime » (runtime du run) reçoit un secret marqueur, en volume et en variable d'environnement.
Un pod « vue du nœud » (runc, privilégié, hostPID, /var/lib/kubelet/pods en lecture seule), sur le même nœud,
simule un administrateur du nœud et cherche le marqueur, **uniquement chez la victime** :
1. fichier du volume secret dans le tmpfs du kubelet (chemin du pod victime, par son UID) ;
2. `/proc/<pid>/environ` des processus du cgroup du pod victime ;
3. mémoire de ces mêmes processus (`/proc/<pid>/mem`) : avec Kata, c'est la mémoire de la VM (QEMU).
Aucune autre donnée du nœud n'est lue ; la preuve ne contient que des compteurs.

Attendu (plan) : lisible depuis le nœud dans les deux runtimes. Kata ne protège pas contre le nœud.
"""

import base64
import json
import secrets as pysecrets

from kvr import secrets

META = {"id": "SCR-04", "category": "SCR", "aspect": "SEC", "priority": "P1",
        "title": "Secret lisible par l'administrateur du nœud ?", "runs": 2, "warmup": False,
        "params": {"max_scan_mib": 4096}}

SCAN = r"""
import os, re, sys, json
uid, marker, max_bytes = sys.argv[1], sys.argv[2].encode(), int(sys.argv[3]) * 1024 * 1024
uid_us = uid.replace("-", "_")
res = {"tmpfs_files": [], "procs": []}
base = f"/host/{uid}/volumes/kubernetes.io~secret"
if os.path.isdir(base):
    for vol in os.listdir(base):
        for f in os.listdir(os.path.join(base, vol)):
            p = os.path.join(base, vol, f)
            if os.path.isfile(p):
                res["tmpfs_files"].append({"file": f, "marker": marker in open(p, "rb").read()})
for pid in filter(str.isdigit, os.listdir("/proc")):
    try:
        cg = open(f"/proc/{pid}/cgroup").read()
    except OSError:
        continue
    if uid not in cg and uid_us not in cg:
        continue
    try:
        comm = open(f"/proc/{pid}/comm").read().strip()
        env_hit = marker in open(f"/proc/{pid}/environ", "rb").read()
    except OSError:
        continue
    mem_hit, scanned = False, 0
    try:
        with open(f"/proc/{pid}/maps") as maps, open(f"/proc/{pid}/mem", "rb", 0) as mem:
            for line in maps:
                lo, hi = (int(x, 16) for x in line.split()[0].split("-"))
                if "r" not in line.split()[1] or scanned >= max_bytes:
                    continue
                pos, tail = lo, b""
                while pos < hi and scanned < max_bytes:
                    n = min(16 << 20, hi - pos)
                    try:
                        mem.seek(pos); chunk = mem.read(n)
                    except (OSError, ValueError, OverflowError):
                        break
                    scanned += len(chunk)
                    if marker in tail + chunk:
                        mem_hit = True
                        break
                    tail, pos = chunk[-len(marker):], pos + n
                if mem_hit:
                    break
    except OSError as e:
        comm += f" (mémoire illisible : {e.strerror})"
    res["procs"].append({"comm": comm, "environ": env_hit, "memory": mem_hit, "scanned_mib": scanned >> 20})
print(json.dumps(res))
"""


def run(ctx):
    marker = "kvr-marqueur-" + pysecrets.token_hex(12)
    secrets.create_secret(ctx, "victim", {"value": marker.encode()})
    ctx.apply_template("secret-pod.yaml.j2", name="victim",
                       secret_volumes=[{"name": "s", "secret": "victim"}],
                       env_secrets=[{"var": "KVR_SECRET", "secret": "victim", "key": "value"}])
    ctx.wait("pod/victim", timeout_s=240)
    pod = ctx.get("pod/victim")
    uid, node = pod["metadata"]["uid"], pod["spec"]["nodeName"]

    ctx.grant_scc("privileged")
    ctx.apply_template("host-reader-pod.yaml.j2", name="nodeview", rc="runc", node_name=node,
                       host_pid=True, host_path="/var/lib/kubelet/pods")
    ctx.wait("pod/nodeview", timeout_s=180)
    b64 = base64.b64encode(SCAN.encode()).decode()
    rc, out, err = ctx.exec("nodeview", ["sh", "-c", f"echo {b64} | base64 -d > /tmp/scan.py && "
                                         f"python3 /tmp/scan.py {uid} {marker} {int(ctx.params['max_scan_mib'])}"],
                            timeout_s=600)
    assert rc == 0, f"analyse depuis le nœud en échec : {err.strip()[-300:]}"
    res = json.loads(out.strip().splitlines()[-1])
    ctx.evidence("node-view.json", res)

    tmpfs = any(f["marker"] for f in res["tmpfs_files"])
    env = any(p["environ"] for p in res["procs"])
    mem = [p["comm"] for p in res["procs"] if p["memory"]]
    ctx.metric("readable_node_tmpfs", int(tmpfs), "bool", "lower")
    ctx.metric("readable_proc_environ", int(env), "bool", "lower")
    ctx.metric("readable_process_memory", int(bool(mem)), "bool", "lower")
    procs = ", ".join(f"{p['comm']}({p['scanned_mib']} MiB)" for p in res["procs"])
    ctx.observe(f"{ctx.runtime} : depuis le nœud, secret {'LU' if tmpfs else 'non trouvé'} dans le tmpfs du kubelet, "
                f"{'LU' if env else 'absent'} dans /proc/<pid>/environ, "
                f"{'LU dans la mémoire de ' + ', '.join(mem) if mem else 'non trouvé en mémoire'} ; "
                f"processus du pod vus sur le nœud : {procs or 'aucun'}")
    return "PASS" if tmpfs and (env or mem) else "FAIL"
