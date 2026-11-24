"""SEC-18 : isolation entre pods (processus, mémoire, fichiers, réseau) — qui voit quoi ?

Une « victime » dans le runtime du run (pod restreint) porte quatre marqueurs uniques :
- processus : un processus nommé kvr-proc-<jeton> ;
- mémoire   : une variable kvr-mem-<jeton> dans l'environnement de ce processus (donc en mémoire) ;
- fichier   : /tmp/kvr-file-<jeton> dans son système de fichiers ;
- réseau    : un paquet UDP kvr-net-<jeton> par seconde vers 192.0.2.10 (adresse de documentation, sans destinataire).

Observateurs sur le même nœud :
1. « voisin runc »  : pod runc restreint ordinaire ;
2. « voisin même runtime » : pod restreint du runtime du run (kata ↔ kata, runc ↔ runc) ;
3. « administrateur du nœud » (seulement avec --non-safe) : pod runc privilégié, hostPID, hostNetwork, racine du
   nœud en lecture seule. Cherche les quatre marqueurs : processus (/proc), mémoire des processus du pod
   victime (identifiés par l'UID du pod dans leur cgroup ; avec Kata, c'est la mémoire de la VM), fichiers
   (stockage des conteneurs du nœud), réseau (capture sur les interfaces du nœud pendant 12 s).

Attendu : 1 et 2 ne voient rien, dans les deux runtimes (sinon FAIL). Pour 3, constat sans verdict :
runc → tout visible ; kata → processus invisible (seuls QEMU / virtiofsd apparaissent), mais mémoire, fichiers et
réseau atteignables : Kata protège le nœud du pod, pas le pod du nœud (rôle de CoCo).
"""

from kvr import escape

META = {"id": "SEC-18", "category": "SEC", "aspect": "SEC", "priority": "P1",
        "title": "Isolation entre pods : processus, mémoire, fichiers, réseau", "runs": 2, "warmup": False,
        "params": {"max_scan_mib": 4096, "sniff_s": 12}}

VICTIM = r"""
echo "kvr-file-$KVR_TOKEN" > /tmp/kvr-file-$KVR_TOKEN
export KVR_MEM="kvr-mem-$KVR_TOKEN"
( while :; do echo "kvr-net-$KVR_TOKEN" > /dev/udp/192.0.2.10/9999 2>/dev/null; sleep 1; done ) &
exec -a "kvr-proc-$KVR_TOKEN" sleep infinity
"""

PEER = r"""
import json, os, sys
t = sys.argv[1]
proc, mem, n = False, False, 0
for pid in filter(str.isdigit, os.listdir("/proc")):
    n += 1
    try:
        proc |= ("kvr-proc-" + t).encode() in open(f"/proc/{pid}/cmdline", "rb").read()
        mem |= ("kvr-mem-" + t).encode() in open(f"/proc/{pid}/environ", "rb").read()
    except OSError:
        pass
print(json.dumps({"process": proc, "environ": mem, "visible_procs": n,
                  "file": os.path.exists("/tmp/kvr-file-" + t)}))
"""

NODE_VIEW = r"""
import glob, json, os, socket, sys, time
t, uid, max_bytes, sniff_s = sys.argv[1], sys.argv[2], int(sys.argv[3]) << 20, int(sys.argv[4])
uid_us = uid.replace("-", "_")
P, M, F, N = (s + t for s in ("kvr-proc-", "kvr-mem-", "kvr-file-", "kvr-net-"))
res = {"process_by_name": False, "pod_processes": [], "memory": False, "files": [], "network": False}

# réseau d'abord (le paquet part chaque seconde)
try:
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3)); s.settimeout(1)
    end = time.time() + sniff_s
    while time.time() < end and not res["network"]:
        try:
            pkt, addr = s.recvfrom(65535)
        except socket.timeout:
            continue
        if N.encode() in pkt:
            res["network"] = True; res["network_iface"] = addr[0][:4] + "…"
except OSError as e:
    res["network_error"] = e.strerror

for pid in filter(str.isdigit, os.listdir("/proc")):
    try:
        if P.encode() in open(f"/proc/{pid}/cmdline", "rb").read():
            res["process_by_name"] = True
        cg = open(f"/proc/{pid}/cgroup").read()
    except OSError:
        continue
    if uid not in cg and uid_us not in cg:
        continue
    comm = open(f"/proc/{pid}/comm").read().strip()
    try:
        cmd = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ")[:60].decode(errors="replace")
    except OSError:
        cmd = "?"
    hit, scanned = False, 0
    try:
        with open(f"/proc/{pid}/maps") as maps, open(f"/proc/{pid}/mem", "rb", 0) as mem:
            for line in maps:
                f = line.split()
                if "r" not in f[1] or scanned >= max_bytes:
                    continue
                lo, hi = (int(x, 16) for x in f[0].split("-"))
                pos, tail = lo, b""
                while pos < hi and scanned < max_bytes and not hit:
                    n = min(16 << 20, hi - pos)
                    try:
                        mem.seek(pos); chunk = mem.read(n)
                    except (OSError, ValueError, OverflowError):
                        break
                    scanned += len(chunk); hit = M.encode() in tail + chunk
                    tail, pos = chunk[-len(M):], pos + n
                if hit:
                    break
    except OSError:
        pass
    res["memory"] |= hit
    res["pod_processes"].append({"comm": comm, "cmdline": cmd.replace(t, "<jeton>"), "memory": hit, "scanned_mib": scanned >> 20})

for pattern in ("/host/var/lib/containers/storage/overlay/*/diff/tmp/" + F,
                "/host/run/kata-containers/shared/sandboxes/*/*/*/rootfs/tmp/" + F,
                "/host/run/kata-containers/shared/sandboxes/*/shared/*/rootfs/tmp/" + F):
    res["files"] += [p.split("/")[3] + "/…" for p in glob.glob(pattern)]
print(json.dumps(res))
"""


def run(ctx):
    tok = escape.token()
    victim = escape.deploy(ctx, "victim", run_as_user=1001, allow_pe=False, drop_all=True, seccomp="RuntimeDefault",
                           command=VICTIM, env=[{"name": "KVR_TOKEN", "value": tok}])
    node, uid = victim["spec"]["nodeName"], victim["metadata"]["uid"]
    restricted = dict(run_as_user=1001, allow_pe=False, drop_all=True, seccomp="RuntimeDefault", node_name=node,
                      memory="384Mi")
    escape.deploy(ctx, "peer-runc", rc="runc", **restricted)
    peers = {"voisin runc": "peer-runc"}
    if ctx.runtime != "runc":
        escape.deploy(ctx, "peer-same", **restricted)
        peers[f"voisin {ctx.runtime}"] = "peer-same"
    seen = {label: escape.run_py(ctx, pod, PEER, tok) for label, pod in peers.items()}
    ctx.evidence("peers.json", seen)
    leaks = [f"{label}:{k}" for label, r in seen.items() for k in ("process", "environ", "file") if r[k]]
    ctx.metric("peer_visibility_leaks", len(leaks), "count", "lower")

    node_txt = "vue administrateur du nœud non évaluée (mode sûr)"
    if not ctx.safe_mode:
        ctx.grant_scc("privileged")
        escape.deploy(ctx, "nodeview", rc="runc", privileged=True, run_as_user=0, host_pid=True, host_network=True,
                      node_name=node, memory="512Mi", host_paths=[{"path": "/", "mount": "/host", "ro": True}])
        nv = escape.run_py(ctx, "nodeview", NODE_VIEW, tok, uid, int(ctx.params["max_scan_mib"]),
                           int(ctx.params["sniff_s"]), timeout_s=900)
        ctx.evidence("node-view.json", nv)
        for k, name in (("process_by_name", "node_sees_process"), ("memory", "node_reads_memory"),
                        ("network", "node_captures_network")):
            ctx.metric(name, int(bool(nv[k])), "bool", "lower")
        ctx.metric("node_reads_files", int(bool(nv["files"])), "bool", "lower")
        comms = sorted({p["comm"] for p in nv["pod_processes"]})
        node_txt = (f"administrateur du nœud : processus marqué {'VISIBLE' if nv['process_by_name'] else 'invisible'} "
                    f"(processus du pod vus sur le nœud : {', '.join(comms) or 'aucun'}), mémoire "
                    f"{'LUE' if nv['memory'] else 'non lue'}, fichier {'TROUVÉ' if nv['files'] else 'non trouvé'}, "
                    f"réseau {'CAPTURÉ' if nv['network'] else 'non capturé' + (' (' + nv['network_error'] + ')' if nv.get('network_error') else '')}")
    ctx.observe(f"{ctx.runtime} : voisins ({', '.join(peers)}) : "
                f"{'AUCUNE visibilité' if not leaks else 'VISIBILITÉ ' + ', '.join(leaks)} "
                f"(processus visibles par le voisin runc : {seen['voisin runc']['visible_procs']}) ; {node_txt}")
    return "FAIL" if leaks else "PASS"
