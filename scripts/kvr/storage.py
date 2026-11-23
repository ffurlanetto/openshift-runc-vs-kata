"""Aides pour la phase VOL : choix de la StorageClass d'un backend et description du backend."""

from __future__ import annotations

from .context import Blocked, TestContext

DEFAULT_ANN = ("storageclass.kubernetes.io/is-default-class", "storageclass.beta.kubernetes.io/is-default-class")


def storage_class(ctx: TestContext, backend: str) -> dict:
    """StorageClass à utiliser pour un backend : params `storage_class` (campaign.yaml › overrides), sinon,
    pour le backend « local » seulement, la classe par défaut du cluster. Retourne {name, provisioner, binding}."""
    name = (ctx.params.get("storage_class") or "").strip()
    items = ctx.cluster.get_json("get", "storageclass").get("items", [])
    if name:
        sc = next((s for s in items if s["metadata"]["name"] == name), None)
        if not sc:
            raise Blocked(f"StorageClass {name} introuvable (backend {backend})")
    else:
        if backend != "local":
            raise Blocked(f"backend {backend} : renseigner overrides.<test>.params.storage_class dans campaign.yaml")
        sc = next((s for s in items if any((s["metadata"].get("annotations") or {}).get(a) == "true"
                                           for a in DEFAULT_ANN)), None)
        if not sc:
            raise Blocked("aucune StorageClass par défaut : renseigner params.storage_class")
    return {"name": sc["metadata"]["name"], "provisioner": sc["provisioner"],
            "binding": sc.get("volumeBindingMode", "Immediate")}
