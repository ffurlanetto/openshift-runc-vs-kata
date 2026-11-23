"""POL-04 : Kyverno : conteneurs privilégiés interdits.

Matrice d'admission (voir kvr/policy_tests.py) : pod conforme admis, pod non conforme refusé,
Deployment non conforme refusé (autogen), exécutée pour runc et pour kata.
Policy : policies/kyverno/catalog.yaml → disallow-privileged.
"""

from kvr.policy_tests import admission_matrix

POLICY = "disallow-privileged"

META = {
    "id": "POL-04",
    "category": "POL",
    "aspect": "SEC",
    "priority": "P1",
    "title": "Kyverno : conteneurs privilégiés interdits",
    "runs": 1,
}


def run(ctx):
    return admission_matrix(ctx, POLICY, {"privileged": True})
