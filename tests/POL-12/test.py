"""POL-12 : forcer Kata par policy (mutation + validation).

Policies : force-kata (ajoute runtimeClassName Kata s'il est absent) + require-kata (refuse tout
autre runtime). Vérifie :
- un pod sans runtimeClassName est muté vers Kata ;
- l'overhead de la RuntimeClass est bien renseigné après mutation (sinon le scheduler et les
  quotas ignorent le coût de la VM : point d'attention majeur pour le capacity planning) ;
- un pod qui demande explicitement une autre RuntimeClass existante est refusé.
"""

import time

from kvr import kyverno
from kvr.context import Blocked

META = {"id": "POL-12", "category": "POL", "aspect": "SEC", "priority": "P1",
        "title": "Kyverno : forcer Kata (mutation + validation)", "runs": 1, "warmup": False}


def run(ctx):
    if not ctx.kyverno:
        raise Blocked("Kyverno absent du cluster")
    kata = ctx.kata_runtime_class
    if not ctx.cluster.has_runtime_class(kata):
        raise Blocked(f"RuntimeClass {kata} absente : la mutation produirait des pods non admissibles")
    plain = ctx.render_record("policy-pod.yaml.j2", "sans-runtimeclass", violations={"no_runtime_class": True})

    kyverno.apply_policy(ctx, "force-kata")
    kyverno.apply_policy(ctx, "require-kata")
    # Propagation : attendre que le pod sans runtimeClassName ressorte muté.
    mutated, obj, msg = False, None, ""
    for _ in range(60):
        ok, obj, msg = kyverno.dry_run(ctx.cluster, ctx.namespace, plain)
        if ok and obj and obj["spec"].get("runtimeClassName") == kata:
            mutated = True
            break
        time.sleep(1)
    ctx.metric("mutated_to_kata", int(mutated), "bool", "higher")
    overhead = (obj or {}).get("spec", {}).get("overhead")
    rc_overhead = ctx.cluster.get_json("get", "runtimeclass", kata).get("overhead")
    overhead_ok = bool(overhead) or not rc_overhead
    ctx.metric("overhead_set_after_mutation", int(overhead_ok), "bool", "higher")
    ctx.evidence("mutated-pod.json", obj or {"admitted": False, "message": msg})

    others = [rc["metadata"]["name"] for rc in ctx.cluster.runtime_classes() if rc["metadata"]["name"] != kata]
    bypass_admitted = None
    if others:
        other = ctx.render_record("policy-pod.yaml.j2", f"runtimeclass-{others[0]}",
                                  violations={"runtime_class_override": others[0], "no_runtime_class": True})
        bypass_admitted, _, bmsg = kyverno.dry_run(ctx.cluster, ctx.namespace, other)
        ctx.metric("other_runtime_class_admitted", int(bypass_admitted), "bool", "lower")
        ctx.evidence("bypass.txt", f"runtimeClassName={others[0]} admis={bypass_admitted}\n{bmsg}")

    ctx.observe(f"muté vers {kata}={mutated} ; overhead après mutation={overhead or 'absent'} "
                f"(RuntimeClass : {rc_overhead or 'aucun'}) ; autre RuntimeClass "
                f"{others[0] if others else 'N/A'} admise={bypass_admitted}")
    if not mutated or bypass_admitted:
        return "FAIL"
    return "PASS" if overhead_ok else "PARTIAL"
