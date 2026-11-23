"""POL-18 : « pas de hostNetwork avec Kata » (garde-fou issu de FUN-30).

Sans policy, un pod Kata en hostNetwork est admis et peut rendre le nœud indisponible
(constaté sur ENV-A). Avec la policy disallow-hostnetwork-kata :
  runc : un pod hostNetwork reste ADMIS (usage légitime : agents réseau, etc.) ;
  kata : le même pod hostNetwork avec la RuntimeClass Kata est REFUSÉ.
Vérification par dry-run serveur uniquement : aucun pod hostNetwork n'est créé.
"""

from kvr import kyverno
from kvr.context import Blocked

META = {"id": "POL-18", "category": "POL", "aspect": "SEC", "priority": "P1",
        "title": "Kyverno : pas de hostNetwork avec Kata", "runs": 1, "warmup": False}


def run(ctx):
    if not ctx.kyverno:
        raise Blocked("Kyverno absent du cluster")
    ctx.grant_scc("hostnetwork-v2")
    hostnet = ctx.render_record("probe-pod.yaml.j2", "hostnetwork", host_network=True)
    base_ok, _, base_msg = kyverno.dry_run(ctx.cluster, ctx.namespace, hostnet)
    ctx.metric("hostnetwork_admitted_without_policy", int(base_ok), "bool",
               "lower" if ctx.runtime == "kata" else "higher")
    if not base_ok:
        raise Blocked(f"pod hostNetwork refusé avant la policy (SCC/policy existante) : {base_msg[:250]}")

    kyverno.apply_policy(ctx, "disallow-hostnetwork-kata")
    # Sonde de propagation : toujours un pod Kata en hostNetwork, quel que soit le runtime testé.
    probe = ctx.render_record("probe-pod.yaml.j2", "sonde-kata-hostnetwork", host_network=True,
                              runtime_class_override=ctx.kata_runtime_class)
    delay = kyverno.wait_until(ctx.cluster, ctx.namespace, probe, denied=True)
    if delay is None:
        ctx.observe("la policy n'est jamais devenue active (sonde Kata hostNetwork toujours admise)")
        return "FAIL"
    ctx.metric("policy_propagation", round(delay * 1000), "ms", "lower")

    ok, _, msg = kyverno.dry_run(ctx.cluster, ctx.namespace, hostnet)
    ctx.metric("hostnetwork_admitted_with_policy", int(ok), "bool",
               "lower" if ctx.runtime == "kata" else "higher")
    ctx.evidence("admission.txt", f"sans policy admis={base_ok}\navec policy admis={ok}\n{msg}")
    ctx.observe(f"{ctx.runtime} : pod hostNetwork {'ADMIS' if ok else 'refusé'} avec la policy")
    expected = ctx.runtime != "kata"
    return "PASS" if ok == expected else "FAIL"
