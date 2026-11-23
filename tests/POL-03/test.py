"""POL-03 : Kyverno : plafond des limits.

Matrice d'admission (voir kvr/policy_tests.py) : pod conforme admis, pod non conforme refusé,
Deployment non conforme refusé (autogen), exécutée pour runc et pour kata.
Policy : policies/kyverno/catalog.yaml → limit-max-resources.
"""

from kvr.policy_tests import admission_matrix

POLICY = "limit-max-resources"

META = {
    "id": "POL-03",
    "category": "POL",
    "aspect": "SEC",
    "priority": "P2",
    "title": "Kyverno : plafond des limits",
    "runs": 1,
    "params": {"max_memory": "2Gi", "max_cpu": "2"},
}


def run(ctx):
    return admission_matrix(ctx, POLICY, {"memory_limit": "8Gi"}, params=ctx.params)
