"""Détection des composants du cluster (kubectl seul, sans accès aux nœuds).

Objectif : que chaque constat soit rattaché à une pile précise. « Kata » recouvre des piles différentes
(OSC/runtime Go/QEMU RHEL, kata-deploy/runtime Rust/QEMU upstream, peer pods…) dont le comportement
diffère. Tout ce qui n'est pas détecté avec certitude est marqué « inconnu », jamais deviné.
"""

from __future__ import annotations

import base64
import gzip
import json
import re

from .cluster import Cluster, OcError

# Handlers connus de kata-deploy (upstream) et d'OSC → (shim, hyperviseur)
_HANDLER_HINTS = [
    (r"runtime-rs|dragonball", "rust"),
]
_HYPERVISORS = ["qemu", "clh", "cloud-hypervisor", "fc", "firecracker", "dragonball", "stratovirt", "remote"]

_CNI = [  # (motif de DaemonSet, namespace éventuel, nom du CNI)
    ("ovnkube-node", None, "OVN-Kubernetes"),
    ("sdn", "openshift-sdn", "OpenShift SDN"),
    ("calico-node", None, "Calico"),
    ("cilium", None, "Cilium"),
    ("kube-flannel", None, "Flannel"),
    ("aws-node", None, "Amazon VPC CNI"),
    ("azure-cns", None, "Azure CNI"),
    ("weave-net", None, "Weave"),
    ("kube-router", None, "kube-router"),
    ("antrea-agent", None, "Antrea"),
]


def _json(cluster: Cluster, *args: str) -> dict | None:
    r = cluster.oc(*args, "-o", "json", check=False)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def _image_tag(image: str) -> str:
    if "@" in image:
        return image.split("@", 1)[1][:19]
    return image.rsplit(":", 1)[1] if ":" in image.rsplit("/", 1)[-1] else "latest"


def distribution(cluster: Cluster, nodes: list[dict]) -> dict:
    out = {"kubernetes": cluster.server_version()}
    if cluster.is_openshift:
        cv = _json(cluster, "get", "clusterversion", "version")
        out["distribution"] = "OpenShift"
        out["version"] = cv["status"]["desired"]["version"] if cv else "inconnue"
        infra = _json(cluster, "get", "infrastructure", "cluster")
        if infra:
            st = infra.get("status") or {}
            out["infrastructure"] = (st.get("platformStatus") or {}).get("type") or st.get("platform") or "inconnue"
            out["topology"] = (infra.get("status") or {}).get("controlPlaneTopology")
        return out
    n = nodes[0] if nodes else {}
    info = (n.get("status") or {}).get("nodeInfo", {})
    labels = (n.get("metadata") or {}).get("labels", {})
    provider = (n.get("spec") or {}).get("providerID", "")
    kubelet = info.get("kubeletVersion", "")
    if "+k3s" in kubelet:
        dist = "k3s"
    elif "+rke2" in kubelet:
        dist = "RKE2"
    elif any(k.startswith("eks.amazonaws.com") for k in labels) or "-eks-" in kubelet:
        dist = "EKS"
    elif any(k.startswith("kubernetes.azure.com") for k in labels):
        dist = "AKS"
    elif any(k.startswith("cloud.google.com/gke") for k in labels) or "-gke." in kubelet:
        dist = "GKE"
    elif "node.k0sproject.io" in str(labels) or "+k0s" in kubelet:
        dist = "k0s"
    elif "microk8s" in str(labels):
        dist = "MicroK8s"
    else:
        dist = "Kubernetes (vanilla ou non identifiée)"
    out.update({"distribution": dist, "version": kubelet,
                "infrastructure": provider.split(":", 1)[0] if provider else "inconnue"})
    return out


def node_stack(nodes: list[dict]) -> dict:
    infos = [(n.get("status") or {}).get("nodeInfo", {}) for n in nodes]
    uniq = lambda k: sorted({i.get(k, "?") for i in infos})  # noqa: E731
    return {"container_runtime": uniq("containerRuntimeVersion"), "os_image": uniq("osImage"),
            "kernel": uniq("kernelVersion"), "arch": uniq("architecture"), "nodes": len(nodes)}


def cni(cluster: Cluster) -> str:
    ds = _json(cluster, "get", "daemonsets", "-A")
    if not ds:
        return "inconnu (liste des DaemonSets non autorisée)"
    names = [(d["metadata"]["name"], d["metadata"]["namespace"]) for d in ds.get("items", [])]
    for pattern, ns, label in _CNI:
        for name, dns in names:
            if pattern in name and (ns is None or ns == dns):
                return label
    return "inconnu"


def _rc_detail(rc: dict) -> dict:
    handler = rc.get("handler", "")
    shim = "inconnu"
    for pattern, kind in _HANDLER_HINTS:
        if re.search(pattern, handler):
            shim = kind
    hyp = next((h for h in _HYPERVISORS if h in handler), None)
    return {"handler": handler, "shim": shim, "hypervisor": hyp or "inconnu",
            "overhead": (rc.get("overhead") or {}).get("podFixed"),
            "node_selector": (rc.get("scheduling") or {}).get("nodeSelector")}


def kata(cluster: Cluster) -> dict:
    """Installation de Kata : OSC (KataConfig + CSV), kata-deploy (Helm/DaemonSet/Job), ou inconnue."""
    rcs = (_json(cluster, "get", "runtimeclass") or {}).get("items", [])
    kata_rcs = {r["metadata"]["name"]: _rc_detail(r) for r in rcs if "kata" in r.get("handler", "")
                or r["metadata"]["name"].startswith("kata")}
    out: dict = {"runtime_classes": kata_rcs, "install": "absent" if not kata_rcs else "inconnue",
                 "version": "inconnue"}
    if not kata_rcs:
        return out

    # OSC : CRD KataConfig + ClusterServiceVersion de l'opérateur
    kc = _json(cluster, "get", "kataconfigs.kataconfiguration.openshift.io")
    if kc and kc.get("items"):
        out["install"] = "OpenShift sandboxed containers (OSC)"
        csvs = _json(cluster, "get", "csv", "-A") or {}
        for c in csvs.get("items", []):
            if "sandboxed-containers" in c["metadata"]["name"]:
                out["version"] = c["spec"].get("version", c["metadata"]["name"])
                break
        spec = kc["items"][0].get("spec") or {}
        out["osc_peer_pods"] = bool(spec.get("enablePeerPods"))
        out["osc_kataconfig_status"] = {k: v for k, v in (kc["items"][0].get("status") or {}).items()
                                        if k in ("runtimeClasses", "kataNodes", "conditions")}
        # OSC (runtime Go) : handler « kata » sans suffixe → shim Go ; « kata-remote » → peer pods
        for name, d in kata_rcs.items():
            if d["shim"] == "inconnu":
                d["shim"] = "go"
            if "remote" in d["handler"]:
                d["hypervisor"] = "remote (peer pods)"
            elif d["hypervisor"] == "inconnu":
                d["hypervisor"] = "qemu (RHEL)"
        return out

    # kata-deploy : 1) release Helm (secret helm.sh/release.v1, survit aux Jobs supprimés)
    secs = _json(cluster, "get", "secrets", "-A", "-l", "owner=helm") or {}
    rel = [s for s in secs.get("items", []) if "kata-deploy" in s["metadata"]["labels"].get("name", "")
           and s["metadata"]["labels"].get("status") == "deployed"]
    if rel:
        s = rel[0]
        out.update({"install": "kata-deploy (upstream, Helm)", "namespace": s["metadata"]["namespace"],
                    "helm_revision": s["metadata"]["labels"].get("version")})
        try:
            raw = base64.b64decode(base64.b64decode(s["data"]["release"]))
            meta = json.loads(gzip.decompress(raw))["chart"]["metadata"]
            out["version"] = meta.get("appVersion") or meta.get("version")
            out["chart"] = f"{meta.get('name')} {meta.get('version')}"
        except (KeyError, ValueError, OSError):
            pass
    # 2) DaemonSet / pod encore présent avec l'image kata-deploy (mode daemonset, ou install en cours)
    if out["install"] == "inconnue":
        for kind in ("daemonsets", "pods"):
            for o in (_json(cluster, "get", kind, "-A") or {}).get("items", []):
                spec = o["spec"].get("template", {}).get("spec", o["spec"]) if kind != "pods" else o["spec"]
                img = next((c["image"] for c in spec.get("containers", []) + spec.get("initContainers", [])
                            if "kata-deploy" in c.get("image", "") and "dispatcher" not in c.get("image", "")), None)
                if img:
                    out.update({"install": "kata-deploy (upstream)", "version": _image_tag(img),
                                "namespace": o["metadata"]["namespace"]})
                    break
            if out["install"] != "inconnue":
                break
    # 3) Labels posés par kata-deploy sur les nœuds
    if out["install"] == "inconnue":
        labelled = (_json(cluster, "get", "nodes", "-l", "katacontainers.io/kata-runtime") or {}).get("items", [])
        if labelled:
            out["install"] = "kata-deploy (upstream, version non lisible)"
    for d in kata_rcs.values():
        if d["shim"] == "inconnu" and out["install"].startswith("kata-deploy") and "remote" not in d["handler"]:
            d["shim"] = "go"  # kata-deploy : les handlers sans « runtime-rs » sont le runtime Go
    return out


def detect(cluster: Cluster, selector: dict | None = None) -> dict:
    try:
        nodes = cluster.nodes(selector)
    except OcError:
        nodes = []
    out = {"cluster": distribution(cluster, nodes), "nodes": node_stack(nodes)}
    for key, fn in (("cni", cni), ("kata", kata)):
        try:
            out[key] = fn(cluster)
        except OcError as e:
            out[key] = f"inconnu ({str(e)[:120]})"
    return out


def summary_lines(c: dict) -> list[tuple[str, str]]:
    cl, nd, k = c["cluster"], c["nodes"], c.get("kata")
    lines = [
        ("distribution", f"{cl.get('distribution')} {cl.get('version')} (k8s {cl.get('kubernetes')}), "
                         f"infra {'None (sans intégration cloud)' if cl.get('infrastructure') == 'None' else cl.get('infrastructure', 'inconnue')}"),
        ("nœuds", f"{nd['nodes']} nœud(s), CRI {', '.join(nd['container_runtime'])}, OS {', '.join(nd['os_image'])}"),
        ("CNI", str(c.get("cni"))),
    ]
    if isinstance(k, dict):
        lines.append(("kata", f"{k['install']}, version {k['version']}"
                              + (", peer pods" if k.get("osc_peer_pods") else "")))
        for name, d in k["runtime_classes"].items():
            lines.append((f"RuntimeClass {name}", f"handler {d['handler']}, shim {d['shim']}, "
                                                 f"hyperviseur {d['hypervisor']}, overhead {d['overhead'] or 'aucun'}"))
    return lines
