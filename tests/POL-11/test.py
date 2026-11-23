"""POL-11 : « pod privilégié autorisé seulement dans Kata ».

runc : un pod privilégié sans runtimeClassName Kata doit être REFUSÉ.
kata : le même pod privilégié avec runtimeClassName Kata doit être ADMIS.
Dans les deux cas, un pod non privilégié reste admis.
"""

from kvr import kyverno
from kvr.context import Blocked

META = {"id": "POL-11", "category": "POL", "aspect": "SEC", "priority": "P1",
        "title": "Kyverno : privilégié seulement avec Kata", "runs": 1, "warmup": False}


def run(ctx):
    if not ctx.kyverno:
        raise Blocked("Kyverno absent du cluster")
    normal = ctx.render_record("policy-pod.yaml.j2", "non-privilegie")
    privileged = ctx.render_record("policy-pod.yaml.j2", "privilegie", violations={"privileged": True})
    base_ok, _, base_msg = kyverno.dry_run(ctx.cluster, ctx.namespace, privileged)
    if not base_ok:
        raise Blocked(f"pod privilégié refusé avant la policy (SCC/policy existante) : {base_msg[:250]}")

    kyverno.apply_policy(ctx, "privileged-requires-kata")
    if ctx.runtime == "runc":
        delay = kyverno.wait_until(ctx.cluster, ctx.namespace, privileged, denied=True)
        if delay is not None:
            ctx.metric("policy_propagation", round(delay * 1000), "ms", "lower")
    else:
        # Côté kata, on attend que la policy soit active via un pod privilégié SANS Kata.
        probe = ctx.render_record("policy-pod.yaml.j2", "sonde-sans-kata",
                                  violations={"privileged": True, "no_runtime_class": True})
        kyverno.wait_until(ctx.cluster, ctx.namespace, probe, denied=True)

    ok_n, _, _ = kyverno.dry_run(ctx.cluster, ctx.namespace, normal)
    ok_p, _, msg_p = kyverno.dry_run(ctx.cluster, ctx.namespace, privileged)
    ctx.metric("unprivileged_admitted", int(ok_n), "bool", "higher")
    ctx.metric("privileged_admitted", int(ok_p), "bool", "higher" if ctx.runtime == "kata" else "lower")
    ctx.evidence("admission.txt", f"non privilégié admis={ok_n}\nprivilégié admis={ok_p}\n{msg_p}")
    ctx.observe(f"{ctx.runtime} : pod privilégié {'ADMIS' if ok_p else 'refusé'}")
    expected = ctx.runtime == "kata"
    return "PASS" if ok_n and ok_p == expected else "FAIL"
