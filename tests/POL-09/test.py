"""POL-09 : Kyverno : seccomp RuntimeDefault obligatoire.

Matrice d'admission (voir kvr/policy_tests.py) : pod conforme admis, pod non conforme refusé,
Deployment non conforme refusé (autogen), exécutée pour runc et pour kata.
Policy : policies/kyverno/catalog.yaml → restrict-seccomp.
"""

from kvr.policy_tests import admission_matrix

POLICY = "restrict-seccomp"

META = {
    "id": "POL-09",
    "category": "POL",
    "aspect": "SEC",
    "priority": "P2",
    "title": "Kyverno : seccomp RuntimeDefault obligatoire",
    "runs": 1,
}


def run(ctx):
    return admission_matrix(ctx, POLICY, {"no_seccomp": True})
