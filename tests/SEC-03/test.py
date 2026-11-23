"""SEC-03 : quelle part du nœud est visible depuis un pod restreint ?

Inventaire comparatif (pas de verdict PASS/FAIL sur la valeur) : processus, périphériques,
montages, interfaces réseau, CPU et mémoire visibles. Avec runc, la mémoire et les CPU
visibles sont ceux du nœud (fuite d'information) ; avec kata, ceux de la VM.
"""

META = {
    "id": "SEC-03",
    "category": "SEC",
    "aspect": "SEC",
    "priority": "P1",
    "title": "Visibilité du nœud depuis un pod restreint",
}

SCRIPT = r"""
echo "procs=$(ls -d /proc/[0-9]* 2>/dev/null | wc -l)"
echo "block_devices=$(ls /sys/block 2>/dev/null | wc -l)"
echo "dev_nodes=$(ls /dev 2>/dev/null | wc -l)"
echo "mounts=$(wc -l < /proc/self/mounts)"
echo "net_interfaces=$(ls /sys/class/net 2>/dev/null | wc -l)"
echo "cpus=$(nproc --all)"
echo "mem_kib=$(grep MemTotal /proc/meminfo | tr -s ' ' | cut -d' ' -f2)"
echo "---"
echo "## /sys/block"; ls /sys/block 2>&1
echo "## /sys/class/net"; ls /sys/class/net 2>&1
echo "## /dev"; ls /dev 2>&1
echo "## mounts"; cat /proc/self/mounts
echo "## cpuinfo (extrait)"; head -20 /proc/cpuinfo
"""


def run(ctx):
    ctx.apply_template("probe-pod.yaml.j2")
    ctx.wait("pod/probe")
    rc, out, err = ctx.exec("probe", ["bash", "-c", SCRIPT])
    assert rc == 0, f"script d'inventaire en échec : {err}"
    ctx.evidence("inventory.txt", out)

    values = dict(line.split("=", 1) for line in out.split("---")[0].split() if "=" in line)
    units = {"procs": "count", "block_devices": "count", "dev_nodes": "count", "mounts": "count",
             "net_interfaces": "count", "cpus": "count"}
    for key, unit in units.items():
        ctx.metric(f"visible_{key}", int(values[key]), unit, "lower")
    mem_mib = round(int(values["mem_kib"]) / 1024)
    ctx.metric("visible_memory", mem_mib, "MiB", "lower")

    node = ctx.pod_node("probe")["status"]["capacity"]
    node_mem_mib = round(int(node["memory"].removesuffix("Ki")) / 1024)
    ctx.observe(f"mémoire visible {mem_mib} MiB (nœud {node_mem_mib} MiB), "
                f"CPU visibles {values['cpus']} (nœud {node['cpu']})")
    return "PASS"
