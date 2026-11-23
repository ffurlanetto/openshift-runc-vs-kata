"""POL-10 : Kyverno : images par digest obligatoires.

Matrice d'admission (voir kvr/policy_tests.py) : pod conforme admis, pod non conforme refusé,
Deployment non conforme refusé (autogen), exécutée pour runc et pour kata.
Policy : policies/kyverno/catalog.yaml → require-image-digest.
"""

from kvr.policy_tests import admission_matrix

POLICY = "require-image-digest"

META = {
    "id": "POL-10",
    "category": "POL",
    "aspect": "SEC",
    "priority": "P2",
    "title": "Kyverno : images par digest obligatoires",
    "runs": 1,
}


def run(ctx):
    # Image par tag (non épinglée) : déclarée dans campaign.yaml (images.ubi_minimal_tag).
    return admission_matrix(ctx, POLICY, {"image": ctx.images["ubi_minimal_tag"]})
