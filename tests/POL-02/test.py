"""POL-02 : Kyverno : requests et limits obligatoires.

Matrice d'admission (voir kvr/policy_tests.py) : pod conforme admis, pod non conforme refusé,
Deployment non conforme refusé (autogen), exécutée pour runc et pour kata.
Policy : policies/kyverno/catalog.yaml → require-requests-limits.
"""

from kvr.policy_tests import admission_matrix

POLICY = "require-requests-limits"

META = {
    "id": "POL-02",
    "category": "POL",
    "aspect": "SEC",
    "priority": "P1",
    "title": "Kyverno : requests et limits obligatoires",
    "runs": 1,
}


def run(ctx):
    return admission_matrix(ctx, POLICY, {"no_resources": True})
