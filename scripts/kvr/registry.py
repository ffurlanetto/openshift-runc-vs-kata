"""Registres d'images : réécriture vers un miroir (Artifactory…) et secret de pull.

Deux modes sur site airgappé :
- le cluster gère lui-même le miroir (OpenShift ImageDigestMirrorSet / miroirs containerd) :
  aucune réécriture, `mirrors: []` ;
- réécriture par le banc : chaque image (et chart OCI) est réécrite selon `mirrors` (préfixe → préfixe).
  Les images étant épinglées par digest, le digest reste identique après réécriture si le miroir
  est un proxy (dépôt remote Artifactory) : la reproductibilité est conservée.
"""

from __future__ import annotations

import copy
import json
import os
import time
from pathlib import Path

from .cluster import Cluster, OcError


def registry_settings(config: dict, profile: dict | None) -> dict:
    """Réglages registre : global (campaign.yaml › registry), surchargé par le profil du cluster."""
    base = copy.deepcopy(config.get("registry") or {})
    base.update((profile or {}).get("registry") or {})
    base.setdefault("mirrors", [])
    base.setdefault("pull_secret", None)
    return base


def rewrite(ref: str, mirrors: list[dict]) -> str:
    """Applique la première règle dont le préfixe correspond (préfixe le plus long d'abord)."""
    scheme = "oci://" if ref.startswith("oci://") else ""
    bare = ref.removeprefix("oci://")
    for rule in sorted(mirrors, key=lambda r: len(r["from"]), reverse=True):
        if bare.startswith(rule["from"]):
            return scheme + rule["to"] + bare[len(rule["from"]):]
    return ref


def resolve_images(config: dict, settings: dict) -> dict:
    return {k: rewrite(v, settings["mirrors"]) for k, v in config["images"].items()}


def resolve_charts(config: dict, settings: dict) -> dict:
    return {k: {**v, "ref": rewrite(v["ref"], settings["mirrors"])} for k, v in (config.get("charts") or {}).items()}


def install_pull_secret(cluster: Cluster, namespace: str, settings: dict) -> None:
    """Crée le secret de pull dans le namespace de test et l'attache au ServiceAccount `default`.

    pull_secret:
      name: artifactory-pull             # nom dans le namespace de test
      from_namespace: kvr-system         # copie d'un secret existant sur le cluster, ou
      dockerconfigjson_file: ~/.docker/artifactory.json   # fichier local (jamais commité)
    """
    ps = settings.get("pull_secret")
    if not ps:
        return
    name = ps["name"]
    if ps.get("from_namespace"):
        src = cluster.get_json("get", "secret", ps.get("source_name", name), "-n", ps["from_namespace"])
        secret = {"apiVersion": "v1", "kind": "Secret", "type": src["type"], "data": src["data"],
                  "metadata": {"name": name, "namespace": namespace}}
        cluster.oc("create", "-f", "-", input=json.dumps(secret))
    elif ps.get("dockerconfigjson_file"):
        path = Path(os.path.expanduser(ps["dockerconfigjson_file"]))
        if not path.exists():
            raise OcError(f"pull_secret.dockerconfigjson_file introuvable : {path}")
        cluster.oc("create", "secret", "generic", name, "-n", namespace,
                   "--type=kubernetes.io/dockerconfigjson", f"--from-file=.dockerconfigjson={path}")
    else:
        raise OcError("pull_secret : préciser from_namespace ou dockerconfigjson_file")
    # Le ServiceAccount `default` est créé de façon asynchrone par le contrôleur.
    for _ in range(30):
        if cluster.oc("get", "sa", "default", "-n", namespace, check=False).returncode == 0:
            break
        time.sleep(1)
    cluster.oc("patch", "sa", "default", "-n", namespace, "--type=merge",
               "-p", json.dumps({"imagePullSecrets": [{"name": name}]}))
