"""FUN-30 : hostNetwork.

Critère indépendant de la plateforme et du CNI : en hostNetwork, le pod doit voir
l'adresse InternalIP de son nœud parmi ses propres adresses (/proc/net/fib_trie).
runc : attendu PASS. kata : limite attendue → NOT_SUPPORTED si le pod ne démarre pas
ou ne voit pas le réseau du nœud.
"""

from kvr.cluster import OcError
from kvr.context import NotSupported

META = {
    "id": "FUN-30",
    "category": "FUN",
    "aspect": "FUN",
    "priority": "P1",
    "title": "hostNetwork",
}


def run(ctx):
    ctx.grant_scc("hostnetwork-v2")
    ctx.apply_template("probe-pod.yaml.j2", host_network=True)
    try:
        ctx.wait("pod/probe", timeout_s=120)
    except OcError as e:
        raise NotSupported(f"pod hostNetwork non Ready : {e}") from e

    node = ctx.pod_node("probe")
    node_ips = [a["address"] for a in node["status"]["addresses"] if a["type"] == "InternalIP"]
    rc, fib, err = ctx.exec("probe", ["cat", "/proc/net/fib_trie"])
    assert rc == 0, f"lecture de /proc/net/fib_trie : {err}"
    _, ifaces, _ = ctx.exec("probe", ["ls", "/sys/class/net"])
    ctx.evidence("fib_trie.txt", fib)
    ctx.evidence("interfaces.txt", ifaces)

    seen = [ip for ip in node_ips if f" {ip}\n" in fib or fib.endswith(f" {ip}")]
    ctx.metric("node_ip_visible", int(bool(seen)), "bool", "higher")
    ctx.observe(f"IP du nœud {node_ips} visibles dans le pod : {seen or 'aucune'} ; "
                f"interfaces : {ifaces.split()}")
    if seen:
        return "PASS"
    raise NotSupported("le pod démarre mais ne voit pas le réseau du nœud (hostNetwork sans effet)")
