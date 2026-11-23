"""FUN-30 : hostNetwork.

Critère indépendant de la plateforme et du CNI : en hostNetwork, le pod doit voir
l'adresse InternalIP de son nœud parmi ses propres adresses (/proc/net/fib_trie).

runc : pod réel, attendu PASS.
kata : DANGEREUX. Sur ENV-A (campagne 20261123-131233), le premier pod Kata en hostNetwork
a rendu le nœud injoignable (API server, SSH) : sans netns propre, Kata rattache à sa
micro-VM les interfaces du nœud. Par défaut, on vérifie donc seulement ce que l'admission
laisse passer (dry-run serveur) : si le pod est admis, le risque est présent → NOT_SUPPORTED
avec la recommandation POL-18. Le pod réel n'est créé qu'avec ./run --allow-destructive
(cluster jetable, nœud dédié).
"""

from kvr import kyverno
from kvr.cluster import OcError
from kvr.context import NotSupported

META = {
    "id": "FUN-30",
    "category": "FUN",
    "aspect": "FUN",
    "priority": "P1",
    "title": "hostNetwork",
    "destructive_on": ["kata"],
}


def run(ctx):
    ctx.grant_scc("hostnetwork-v2")
    if ctx.runtime_class and not ctx.allow_destructive:
        manifest = ctx.render_record("probe-pod.yaml.j2", "hostnetwork-dryrun", host_network=True)
        admitted, _, msg = kyverno.dry_run(ctx.cluster, ctx.namespace, manifest)
        ctx.metric("hostnetwork_kata_admitted", int(admitted), "bool", "lower")
        ctx.evidence("dry-run.txt", msg or "admis")
        if not admitted:
            ctx.observe(f"pod Kata en hostNetwork refusé à l'admission : {msg[:200]}")
            return "PASS"
        ctx.observe("pod Kata en hostNetwork ADMIS par le cluster : non exécuté (risque de perte du nœud, "
                    "constaté sur ENV-A). Rejouer avec --allow-destructive sur un cluster jetable.")
        raise NotSupported("hostNetwork non supporté par Kata et non bloqué à l'admission : "
                           "un pod peut rendre le nœud indisponible (cf. POL-18)")

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
