"""POL-06 : Kyverno : capabilities restreintes.

Matrice d'admission (voir kvr/policy_tests.py) : pod conforme admis, pod non conforme refusé,
Deployment non conforme refusé (autogen), exécutée pour runc et pour kata.
Policy : policies/kyverno/catalog.yaml → restrict-capabilities.
"""

from kvr.policy_tests import admission_matrix

POLICY = "restrict-capabilities"

META = {
    "id": "POL-06",
    "category": "POL",
    "aspect": "SEC",
    "priority": "P1",
    "title": "Kyverno : capabilities restreintes",
    "runs": 1,
}


def run(ctx):
    return admission_matrix(ctx, POLICY, {"caps": ["SYS_ADMIN"]})
