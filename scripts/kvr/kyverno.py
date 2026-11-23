"""Kyverno : détection (déjà présent ou non sur le cluster), rendu des policies du catalogue, aides de test.

Le banc n'installe ni ne modifie jamais Kyverno ni les ClusterPolicies existantes : ses policies
sont créées dans le namespace de test et disparaissent avec lui.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import jinja2
import yaml

from .cluster import Cluster, OcError

POLICY_DIR = Path(__file__).resolve().parents[2] / "policies" / "kyverno"
CEL_CRD = "namespacedvalidatingpolicies.policies.kyverno.io"
LEGACY_CRD = "policies.kyverno.io"


def detect(cluster: Cluster) -> dict | None:
    """Retourne {flavor, api_version, version, namespace, enforce_cluster_policies} ou None si absent."""
    def served(crd: str) -> list[str]:
        r = cluster.oc("get", "crd", crd, "-o", "jsonpath={.spec.versions[?(@.served==true)].name}", check=False)
        return r.stdout.split() if r.returncode == 0 else []

    cel_versions, legacy_versions = served(CEL_CRD), served(LEGACY_CRD)
    if not cel_versions and not legacy_versions:
        return None
    if "v1" in cel_versions:
        flavor, api_version = "cel", "v1"
    elif "v1beta1" in cel_versions:
        flavor, api_version = "cel", "v1beta1"
    else:
        flavor, api_version = "legacy", "v1"

    version, namespace = "inconnue", None
    r = cluster.oc("get", "deployments", "-A", "-l", "app.kubernetes.io/part-of=kyverno", "-o", "json", check=False)
    if r.returncode == 0:
        for d in json.loads(r.stdout)["items"]:
            if "admission" in d["metadata"]["name"]:
                image = d["spec"]["template"]["spec"]["containers"][0]["image"]
                version = image.rsplit(":", 1)[-1].split("@")[0]
                namespace = d["metadata"]["namespace"]
    return {"flavor": flavor, "api_version": api_version, "version": version, "namespace": namespace,
            "enforce_cluster_policies": enforce_cluster_policies(cluster)}


def enforce_cluster_policies(cluster: Cluster) -> list[str]:
    """ClusterPolicies déjà présentes en mode bloquant : elles s'appliquent aussi aux pods de test."""
    names = []
    r = cluster.oc("get", "clusterpolicies.kyverno.io", "-o", "json", check=False)
    if r.returncode == 0:
        for p in json.loads(r.stdout)["items"]:
            spec = p.get("spec", {})
            rules_enforce = any((rule.get("validate") or {}).get("failureAction") == "Enforce"
                                for rule in spec.get("rules", []))
            if spec.get("validationFailureAction") in ("Enforce", "enforce") or rules_enforce:
                names.append(f"ClusterPolicy/{p['metadata']['name']}")
    r = cluster.oc("get", "validatingpolicies.policies.kyverno.io", "-o", "json", check=False)
    if r.returncode == 0:
        for p in json.loads(r.stdout)["items"]:
            if "Deny" in (p.get("spec", {}).get("validationActions") or ["Deny"]):
                names.append(f"ValidatingPolicy/{p['metadata']['name']}")
    return names


def _catalog() -> dict:
    return yaml.safe_load((POLICY_DIR / "catalog.yaml").read_text())


def render_policy(kyverno: dict, policy_id: str, namespace: str, kata_rc: str,
                  actions: list[str] | None = None, params: dict | None = None) -> str:
    """Rend une policy du catalogue pour la saveur de Kyverno détectée."""
    cat = _catalog()
    if policy_id in cat["policies"]:
        kind, p = "validate", cat["policies"][policy_id]
    elif policy_id in cat["mutations"]:
        kind, p = "mutate", cat["mutations"][policy_id]
    else:
        raise KeyError(f"policy inconnue dans le catalogue : {policy_id}")
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    # 1) substitution des paramètres dans chaque chaîne du catalogue (expressions, messages)
    expr_vars = {"kata_rc": kata_rc, "params": params or {}}

    def subst(node):
        if isinstance(node, str):
            return env.from_string(node).render(**expr_vars) if "{{" in node else node
        if isinstance(node, dict):
            return {k: subst(v) for k, v in node.items()}
        if isinstance(node, list):
            return [subst(v) for v in node]
        return node

    p = subst(p)
    # 2) rendu de la ressource Kyverno
    template = "cel.yaml.j2" if kyverno["flavor"] == "cel" else "legacy.yaml.j2"
    tenv = jinja2.Environment(loader=jinja2.FileSystemLoader(str(POLICY_DIR)), undefined=jinja2.StrictUndefined)
    tenv.filters["tojson"] = lambda v: json.dumps(v, ensure_ascii=False)
    tpl = tenv.get_template(template)
    return tpl.render(kind=kind, p=p, id=policy_id, namespace=namespace,
                      actions=actions or ["Deny"], api_version=kyverno["api_version"],
                      variables=cat["common_variables"])


def dry_run(cluster: Cluster, namespace: str, manifest: str) -> tuple[bool, dict | None, str]:
    """Création à blanc côté serveur (traverse toute l'admission, webhooks Kyverno compris).
    Retourne (admis, objet résultant après mutations, message d'erreur/avertissements)."""
    r = cluster.oc("create", "--dry-run=server", "-n", namespace, "-o", "json", "-f", "-",
                   input=manifest, check=False)
    if r.returncode == 0:
        return True, json.loads(r.stdout), r.stderr.strip()
    return False, None, r.stderr.strip()


def wait_until(cluster: Cluster, namespace: str, manifest: str, *, denied: bool = False,
               warned: bool = False, timeout_s: int = 60) -> float | None:
    """Attend qu'une policy fraîchement créée soit active (webhook propagé) en sondant par dry-run.
    Retourne le délai en secondes, ou None si l'état attendu n'est jamais atteint."""
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout_s:
        admitted, _, msg = dry_run(cluster, namespace, manifest)
        if (denied and not admitted) or (warned and admitted and "Warning" in msg):
            return time.perf_counter() - t0
        time.sleep(1)
    return None


def apply_policy(ctx, policy_id: str, actions: list[str] | None = None, params: dict | None = None) -> None:
    if not ctx.kyverno:
        from .context import Blocked
        raise Blocked("Kyverno absent du cluster (voir ./precheck --phases POL)")
    text = render_policy(ctx.kyverno, policy_id, ctx.namespace, ctx.kata_runtime_class or "kata",
                         actions, params)
    ctx.evidence(f"policy-{policy_id}.yaml", text)
    try:
        ctx.cluster.oc("apply", "-n", ctx.namespace, "-f", "-", input=text)
    except OcError as e:
        raise RuntimeError(f"création de la policy {policy_id} refusée : {e}") from e
