"""POL-05 : Kyverno : escalade de privilèges interdite.

Matrice d'admission (voir kvr/policy_tests.py) : pod conforme admis, pod non conforme refusé,
Deployment non conforme refusé (autogen), exécutée pour runc et pour kata.
Policy : policies/kyverno/catalog.yaml → disallow-privilege-escalation.
"""

from kvr.policy_tests import admission_matrix

POLICY = "disallow-privilege-escalation"

META = {
    "id": "POL-05",
    "category": "POL",
    "aspect": "SEC",
    "priority": "P1",
    "title": "Kyverno : escalade de privilèges interdite",
    "runs": 1,
}


def run(ctx):
    return admission_matrix(ctx, POLICY, {"privesc": True})
