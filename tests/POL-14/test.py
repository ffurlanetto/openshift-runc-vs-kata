"""POL-14 : tentatives de contournement d'une policy en Enforce.

Policies actives : disallow-privileged + require-run-as-nonroot. Vecteurs testés :
- Job et CronJob non conformes (règles autogen des contrôleurs) ;
- conteneur éphémère privilégié ajouté à un pod conforme en cours d'exécution (kubectl debug).
Chaque vecteur admis = contournement (FAIL).
"""

import json

import yaml

from kvr import kyverno
from kvr.context import Blocked

META = {"id": "POL-14", "category": "POL", "aspect": "SEC", "priority": "P1",
        "title": "Kyverno : contournements (Job, CronJob, conteneur éphémère)", "runs": 1, "warmup": False}


def _wrap(kind: str, pod_manifest: dict, ns: str) -> str:
    spec = pod_manifest["spec"]
    spec["restartPolicy"] = "Never"
    tmpl = {"metadata": {"labels": {"app": "bypass"}}, "spec": spec}
    if kind == "Job":
        obj = {"apiVersion": "batch/v1", "kind": "Job", "metadata": {"name": "bypass-job", "namespace": ns},
               "spec": {"template": tmpl}}
    else:
        obj = {"apiVersion": "batch/v1", "kind": "CronJob", "metadata": {"name": "bypass-cron", "namespace": ns},
               "spec": {"schedule": "0 0 1 1 *", "jobTemplate": {"spec": {"template": tmpl}}}}
    return json.dumps(obj)


def run(ctx):
    if not ctx.kyverno:
        raise Blocked("Kyverno absent du cluster")
    violating = ctx.render_record("policy-pod.yaml.j2", "privilegie-root",
                                  violations={"privileged": True, "root": True})
    compliant = ctx.render_record("policy-pod.yaml.j2", "conforme", name="target")

    kyverno.apply_policy(ctx, "disallow-privileged")
    kyverno.apply_policy(ctx, "require-run-as-nonroot")
    if kyverno.wait_until(ctx.cluster, ctx.namespace, violating, denied=True) is None:
        ctx.observe("policies jamais actives : le pod direct non conforme reste admis")
        return "FAIL"

    results = {}
    for kind in ("Job", "CronJob"):
        ok, _, msg = kyverno.dry_run(ctx.cluster, ctx.namespace, _wrap(kind, yaml.safe_load(violating), ctx.namespace))
        results[kind] = ok
        ctx.evidence(f"{kind.lower()}.txt", f"admis={ok}\n{msg}")

    # Conteneur éphémère privilégié sur un pod conforme qui tourne
    ctx.cluster.oc("create", "-n", ctx.namespace, "-f", "-", input=compliant)
    ctx.wait("pod/target", timeout_s=240)
    r = ctx.cluster.oc("debug", "-n", ctx.namespace, "pod/target", "--profile=sysadmin",
                       f"--image={ctx.images['ubi_minimal']}", "--container=debugger",
                       "--", "true", check=False, timeout=120)
    eph = json.loads(ctx.cluster.oc("get", "pod", "target", "-n", ctx.namespace, "-o", "json").stdout)
    results["EphemeralContainer"] = any(c["name"] == "debugger" for c in eph["spec"].get("ephemeralContainers", []))
    ctx.evidence("ephemeral.txt", f"admis={results['EphemeralContainer']}\n{r.stdout}\n{r.stderr}")

    for vector, admitted in results.items():
        ctx.metric(f"bypass_{vector.lower()}_admitted", int(admitted), "bool", "lower")
    bypassed = [k for k, v in results.items() if v]
    ctx.observe(f"vecteurs admis malgré Enforce : {bypassed or 'aucun'}")
    return "FAIL" if bypassed else "PASS"
