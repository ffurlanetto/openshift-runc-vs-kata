"""POL-08 : Kyverno : hostPath interdit.

Matrice d'admission (voir kvr/policy_tests.py) : pod conforme admis, pod non conforme refusé,
Deployment non conforme refusé (autogen), exécutée pour runc et pour kata.
Policy : policies/kyverno/catalog.yaml → disallow-host-path.
"""

from kvr.policy_tests import admission_matrix

POLICY = "disallow-host-path"

META = {
    "id": "POL-08",
    "category": "POL",
    "aspect": "SEC",
    "priority": "P1",
    "title": "Kyverno : hostPath interdit",
    "runs": 1,
}


def run(ctx):
    return admission_matrix(ctx, POLICY, {"host_path": True})
