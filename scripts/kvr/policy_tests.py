"""Aides communes aux tests de la phase POL (Kyverno)."""

from __future__ import annotations

from . import kyverno
from .context import Blocked

TEMPLATE = "policy-pod.yaml.j2"


def admission_matrix(ctx, policy_id: str, violations: dict, params: dict | None = None) -> str:
    """Matrice d'admission d'une policy de validation, pour le runtime courant.

    1. sans policy : pod conforme et pod non conforme (effet des autres couches : SCC, PSA, policies existantes)
    2. policy en Enforce (Deny) : le pod conforme passe, le pod non conforme est refusé
    3. contournement par un contrôleur : Deployment non conforme (règles autogen)
    """
    if not ctx.kyverno:
        raise Blocked("Kyverno absent du cluster")
    compliant = ctx.render_record(TEMPLATE, "conforme")
    violating = ctx.render_record(TEMPLATE, "non-conforme", violations=violations)
    deploy = ctx.render_record(TEMPLATE, "deployment-non-conforme", violations=violations, kind="Deployment")

    ok_base, _, msg_base = kyverno.dry_run(ctx.cluster, ctx.namespace, compliant)
    if not ok_base:
        raise Blocked(f"pod conforme refusé AVANT la policy du test (policy existante, SCC, quota…) : {msg_base[:300]}")
    v_base, _, v_base_msg = kyverno.dry_run(ctx.cluster, ctx.namespace, violating)
    ctx.metric("violating_admitted_without_policy", int(v_base), "bool", "lower")
    if not v_base:
        ctx.observe(f"sans policy du test, le pod non conforme est déjà refusé par une autre couche : {v_base_msg[:200]}")

    kyverno.apply_policy(ctx, policy_id, ["Deny"], params)
    delay = kyverno.wait_until(ctx.cluster, ctx.namespace, violating, denied=True, timeout_s=60)
    if delay is not None:
        ctx.metric("policy_propagation", round(delay * 1000), "ms", "lower")

    ok_c, _, msg_c = kyverno.dry_run(ctx.cluster, ctx.namespace, compliant)
    ok_v, _, msg_v = kyverno.dry_run(ctx.cluster, ctx.namespace, violating)
    ok_d, _, msg_d = kyverno.dry_run(ctx.cluster, ctx.namespace, deploy)
    ctx.metric("compliant_admitted_enforce", int(ok_c), "bool", "higher")
    ctx.metric("violating_admitted_enforce", int(ok_v), "bool", "lower")
    ctx.metric("violating_deployment_admitted_enforce", int(ok_d), "bool", "lower")
    ctx.evidence("admission.txt", "\n\n".join([
        f"## sans policy : conforme={ok_base} non-conforme={v_base}\n{v_base_msg}",
        f"## Enforce : conforme={ok_c}\n{msg_c}",
        f"## Enforce : pod non conforme admis={ok_v}\n{msg_v}",
        f"## Enforce : Deployment non conforme admis={ok_d}\n{msg_d}",
    ]))
    ctx.observe(f"Kyverno {ctx.kyverno['version']} ({ctx.kyverno['flavor']}) ; "
                f"Enforce : conforme {'admis' if ok_c else 'REFUSÉ'}, non conforme {'ADMIS' if ok_v else 'refusé'}, "
                f"Deployment non conforme {'ADMIS' if ok_d else 'refusé'}")
    if not ok_c or ok_v:
        return "FAIL"
    return "PARTIAL" if ok_d else "PASS"
