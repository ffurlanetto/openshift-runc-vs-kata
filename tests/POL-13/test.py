"""POL-13 : mode Audit vs Enforce.

En Audit (+ Warn), un pod non conforme est ADMIS, un avertissement est renvoyé au client et
une entrée « fail » apparaît dans le rapport de policy du namespace. Mesure le délai de remontée.
"""

import json
import time

from kvr import kyverno
from kvr.context import Blocked

META = {"id": "POL-13", "category": "POL", "aspect": "SEC", "priority": "P1",
        "title": "Kyverno : mode Audit (admission + rapport)", "runs": 1, "warmup": False}

POLICY = "require-run-as-nonroot"
REPORT_KINDS = ("policyreports.wgpolicyk8s.io", "reports.openreports.io")


def _report_fail(ctx) -> dict | None:
    for kind in REPORT_KINDS:
        r = ctx.cluster.oc("get", kind, "-n", ctx.namespace, "-o", "json", check=False)
        if r.returncode != 0:
            continue
        for rep in json.loads(r.stdout)["items"]:
            for res in rep.get("results", []):
                if res.get("result") == "fail" and POLICY in (res.get("policy") or ""):
                    return {"kind": kind, "result": res}
    return None


def run(ctx):
    if not ctx.kyverno:
        raise Blocked("Kyverno absent du cluster")
    violating = ctx.render_record("policy-pod.yaml.j2", "non-conforme", violations={"root": True})
    base_ok, _, base_msg = kyverno.dry_run(ctx.cluster, ctx.namespace, violating)
    if not base_ok:
        raise Blocked(f"pod root refusé avant la policy (SCC/policy existante) : {base_msg[:250]}")

    kyverno.apply_policy(ctx, POLICY, ["Audit", "Warn"])
    if kyverno.wait_until(ctx.cluster, ctx.namespace, violating, warned=True) is None:
        ctx.observe("aucun avertissement Warn reçu en 60 s")
    t0 = time.perf_counter()
    r = ctx.cluster.oc("create", "-n", ctx.namespace, "-f", "-", input=violating, check=False)
    admitted = r.returncode == 0
    ctx.metric("violating_admitted_audit", int(admitted), "bool", "higher")
    ctx.evidence("create.txt", r.stdout + r.stderr)
    found = None
    while admitted and time.perf_counter() - t0 < 120:
        found = _report_fail(ctx)
        if found:
            break
        time.sleep(3)
    ctx.metric("reported_in_policy_report", int(bool(found)), "bool", "higher")
    if found:
        ctx.metric("report_delay", round(time.perf_counter() - t0, 1), "s", "lower")
        ctx.evidence("report-entry.json", found)
    ctx.observe(f"Audit : pod non conforme admis={admitted}, avertissement client={'Warning' in r.stderr}, "
                f"rapport={'oui (' + found['kind'] + ')' if found else 'non (120 s)'}")
    if not admitted:
        return "FAIL"
    return "PASS" if found else "PARTIAL"
