"""POL-07 : Kyverno : namespaces de l'hôte interdits.

Matrice d'admission (voir kvr/policy_tests.py) : pod conforme admis, pod non conforme refusé,
Deployment non conforme refusé (autogen), exécutée pour runc et pour kata.
Policy : policies/kyverno/catalog.yaml → disallow-host-namespaces.
"""

from kvr.policy_tests import admission_matrix

POLICY = "disallow-host-namespaces"

META = {
    "id": "POL-07",
    "category": "POL",
    "aspect": "SEC",
    "priority": "P1",
    "title": "Kyverno : namespaces de l'hôte interdits",
    "runs": 1,
}


def run(ctx):
    return admission_matrix(ctx, POLICY, {"host_network": True})
