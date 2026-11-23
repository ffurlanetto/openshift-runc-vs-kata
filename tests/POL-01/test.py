"""POL-01 : Kyverno : non-root obligatoire.

Matrice d'admission (voir kvr/policy_tests.py) : pod conforme admis, pod non conforme refusé,
Deployment non conforme refusé (autogen), exécutée pour runc et pour kata.
Policy : policies/kyverno/catalog.yaml → require-run-as-nonroot.
"""

from kvr.policy_tests import admission_matrix

POLICY = "require-run-as-nonroot"

META = {
    "id": "POL-01",
    "category": "POL",
    "aspect": "SEC",
    "priority": "P1",
    "title": "Kyverno : non-root obligatoire",
    "runs": 1,
}


def run(ctx):
    return admission_matrix(ctx, POLICY, {"root": True})
