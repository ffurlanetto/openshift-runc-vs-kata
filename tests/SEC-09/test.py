"""SEC-09 : un pod privilégié peut-il modifier le noyau du nœud (sysctl, module) ?

Attaquant dans le runtime du run : root, `privileged: true`, modules du nœud (/lib/modules) montés en lecture.
1. sysctl : écrit `vm.stat_interval` (valeur +1, sans effet notable), puis le restaure ;
2. module : charge un module inoffensif NON chargé (contrôle de congestion TCP, inactif tant qu'il n'est pas
   sélectionné), par l'appel système init_module, puis le décharge.
Le constat vient d'une sonde runc NON privilégiée sur le même nœud : /proc/sys et /proc/modules y montrent les
valeurs du noyau du nœud. Restauration (sysctl) et déchargement (module) vérifiés par la sonde.

Attendu (plan) : runc → le noyau du nœud est modifié ; kata → seulement celui de la VM (module du nœud
incompatible avec le noyau invité). PASS = constat conforme à l'attendu ET nœud remis en l'état.
"""

from kvr import escape

META = {"intrusive": "pod privilégié qui modifie un sysctl du nœud (restauré) et charge un module noyau inoffensif "
                     "(déchargé)",
        "id": "SEC-09", "category": "SEC", "aspect": "SEC", "priority": "P2",
        "title": "Pod privilégié : sysctl et module noyau du nœud", "runs": 2, "warmup": False,
        "params": {"modules": ["tcp_htcp", "tcp_vegas", "tcp_illinois", "tcp_veno", "nlmon"]}}

NODE_STATE = r"""
import json, os, sys
mods = {l.split()[0] for l in open("/proc/modules")}
print(json.dumps({"kernel": os.uname().release, "stat_interval": open("/proc/sys/vm/stat_interval").read().strip(),
                  "loaded": sorted(m for m in sys.argv[1].split(",") if m in mods)}))
"""

ATTACK_MODULE = r"""
import ctypes, glob, json, lzma, os, platform, sys
node_kernel, candidates, nr_init, nr_del = sys.argv[1], sys.argv[2].split(","), int(sys.argv[3]), int(sys.argv[4])
action = sys.argv[5]
libc = ctypes.CDLL(None, use_errno=True)
res = {"guest_kernel": platform.release()}
if action == "load":
    for name in candidates:
        files = glob.glob(f"/hostmods/{node_kernel}/kernel/**/{name}.ko*", recursive=True)
        if files:
            break
    else:
        print(json.dumps({**res, "module": None, "result": "aucun module candidat sur le nœud"})); sys.exit()
    data = open(files[0], "rb").read()
    if files[0].endswith(".xz"):
        data = lzma.decompress(data)
    ret = libc.syscall(nr_init, ctypes.c_char_p(data), ctypes.c_ulong(len(data)), b"")
    e = ctypes.get_errno()
    res.update(module=name, result="chargé" if ret == 0 else f"refusé ({os.strerror(e)})")
else:
    ret = libc.syscall(nr_del, action.encode(), 0o4000)  # O_NONBLOCK
    res.update(module=action, result="déchargé" if ret == 0 else f"échec ({os.strerror(ctypes.get_errno())})")
print(json.dumps(res))
"""


def run(ctx):
    ctx.grant_scc("privileged")
    candidates = ",".join(ctx.params["modules"])
    probe = escape.deploy(ctx, "nodecheck", rc="runc", run_as_user=1001, allow_pe=False, drop_all=True,
                          seccomp="RuntimeDefault")
    node = probe["spec"]["nodeName"]
    arch = 0 if ctx.cluster.node(node)["status"]["nodeInfo"]["architecture"] in ("amd64", "x86_64") else 1
    nr_init, nr_del = escape.SYSCALLS["init_module"][arch], escape.SYSCALLS["delete_module"][arch]
    before = escape.run_py(ctx, "nodecheck", NODE_STATE, candidates)
    escape.deploy(ctx, "attacker", privileged=True, run_as_user=0, node_name=node, memory="512Mi",
                  host_paths=[{"path": "/lib/modules", "mount": "/hostmods", "ro": True}])

    # 1. sysctl
    old = before["stat_interval"]
    new = str(int(old) + 1)
    rc, out, err = ctx.exec("attacker", ["sh", "-c", f"echo {new} > /proc/sys/vm/stat_interval && echo ok"])
    sysctl_written = rc == 0 and "ok" in out
    during = escape.run_py(ctx, "nodecheck", NODE_STATE, candidates)
    ctx.exec("attacker", ["sh", "-c", f"echo {old} > /proc/sys/vm/stat_interval"])
    after_sysctl = escape.run_py(ctx, "nodecheck", NODE_STATE, candidates)
    sysctl_on_node = during["stat_interval"] == new
    sysctl_restored = after_sysctl["stat_interval"] == old

    # 2. module
    load = escape.run_py(ctx, "attacker", ATTACK_MODULE, before["kernel"],
                         ",".join(m for m in ctx.params["modules"] if m not in before["loaded"]), nr_init, nr_del, "load")
    mid = escape.run_py(ctx, "nodecheck", NODE_STATE, candidates)
    module = load.get("module")
    module_on_node = bool(module) and module in mid["loaded"] and module not in before["loaded"]
    unload = None
    if load.get("result") == "chargé" and module:
        unload = escape.run_py(ctx, "attacker", ATTACK_MODULE, before["kernel"], "", nr_init, nr_del, module)
    final = escape.run_py(ctx, "nodecheck", NODE_STATE, candidates)
    module_cleaned = sorted(final["loaded"]) == sorted(before["loaded"])
    ctx.evidence("states.json", {"before": before, "during_sysctl": during, "after_sysctl": after_sysctl,
                                 "after_load": mid, "final": final, "load": load, "unload": unload,
                                 "sysctl_written_in_pod": sysctl_written})

    ctx.metric("node_sysctl_modified", int(sysctl_on_node), "bool", "lower")
    ctx.metric("node_module_loaded", int(module_on_node), "bool", "lower")
    ctx.metric("node_left_modified", int(not (sysctl_restored and module_cleaned)), "bool", "lower")
    ctx.observe(f"{ctx.runtime} : sysctl écrit dans le pod={'oui' if sysctl_written else 'non'}, "
                f"vu sur le NŒUD={'OUI' if sysctl_on_node else 'non'} (restauré={'oui' if sysctl_restored else 'NON'}) ; "
                f"module {module or '-'} : {load.get('result')} (noyau du pod {load.get('guest_kernel')}, "
                f"nœud {before['kernel']}), chargé sur le NŒUD={'OUI' if module_on_node else 'non'}"
                f"{', ' + unload['result'] if unload else ''} ; nœud remis en l'état={'oui' if sysctl_restored and module_cleaned else 'NON'}")
    if not (sysctl_restored and module_cleaned):
        return "FAIL"
    impacted = sysctl_on_node or module_on_node
    return "PASS" if impacted == (ctx.runtime == "runc") else "FAIL"
