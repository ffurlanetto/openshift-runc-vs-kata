"""Accès au cluster via kubectl uniquement (OpenShift ou Kubernetes, local ou distant).

OpenShift est détecté automatiquement ; aucune dépendance à `oc`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess


class OcError(RuntimeError):
    """Erreur d'un appel kubectl (nom historique conservé pour les tests)."""


PRESSURE_CONDITIONS = ("DiskPressure", "MemoryPressure", "PIDPressure")


def kubectl_path() -> str:
    found = shutil.which("kubectl")
    if not found:
        raise OcError("kubectl introuvable dans le PATH")
    return found


def _raw(*args: str, timeout: float = 30) -> subprocess.CompletedProcess:
    return subprocess.run([kubectl_path(), *args], capture_output=True, text=True,
                          env=dict(os.environ), timeout=timeout)


def list_contexts() -> list[dict]:
    """Contextes du kubeconfig courant (KUBECONFIG ou ~/.kube/config) avec leur API server."""
    r = _raw("config", "view", "-o", "json")
    if r.returncode != 0:
        raise OcError(f"lecture du kubeconfig impossible : {r.stderr.strip()}")
    cfg = json.loads(r.stdout or "{}")
    servers = {c["name"]: c["cluster"].get("server", "?") for c in cfg.get("clusters") or []}
    current = cfg.get("current-context")
    out = []
    for c in cfg.get("contexts") or []:
        ctx = c.get("context", {})
        out.append({"name": c["name"], "cluster": ctx.get("cluster"), "user": ctx.get("user"),
                    "namespace": ctx.get("namespace"), "server": servers.get(ctx.get("cluster"), "?"),
                    "current": c["name"] == current})
    return out


class Cluster:
    """Enveloppe kubectl liée à un contexte explicite."""

    def __init__(self, context: str) -> None:
        self.kubectl = kubectl_path()
        self.context = context
        self.env = dict(os.environ)
        self._platform: str | None = None

    def oc(self, *args: str, input: str | None = None, check: bool = True,
           timeout: float = 120) -> subprocess.CompletedProcess:
        """Exécute `kubectl --context <ctx> ...` (nom `oc` conservé pour la lisibilité des tests)."""
        cmd = [self.kubectl, "--context", self.context, *args]
        try:
            r = subprocess.run(cmd, input=input, capture_output=True, text=True,
                               env=self.env, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise OcError(f"kubectl {' '.join(args)} : délai dépassé ({timeout}s)") from e
        if check and r.returncode != 0:
            raise OcError(f"kubectl {' '.join(args)} -> rc={r.returncode} : {r.stderr.strip()}")
        return r

    def get_json(self, *args: str) -> dict:
        return json.loads(self.oc(*args, "-o", "json").stdout)

    # ---------- identification
    @property
    def platform(self) -> str:
        if self._platform is None:
            r = self.oc("api-resources", "--api-group=config.openshift.io", "-o", "name", check=False)
            self._platform = "openshift" if r.returncode == 0 and "clusterversions" in r.stdout else "kubernetes"
        return self._platform

    @property
    def is_openshift(self) -> bool:
        return self.platform == "openshift"

    def api_server(self) -> str:
        return self.oc("config", "view", "--minify", "-o",
                       "jsonpath={.clusters[0].cluster.server}").stdout.strip()

    def server_version(self) -> str:
        return json.loads(self.oc("version", "-o", "json").stdout)["serverVersion"]["gitVersion"]

    def platform_version(self) -> str:
        server = self.server_version()  # lève OcError si le cluster est injoignable
        if self.is_openshift:
            try:
                cv = self.get_json("get", "clusterversion", "version")
                return f"OpenShift {cv['status']['desired']['version']}"
            except OcError:
                return f"OpenShift (version illisible avec ce compte, Kubernetes {server})"
        return f"Kubernetes {server}"

    def can_i(self, verb: str, resource: str, namespace: str | None = None) -> bool:
        args = ["auth", "can-i", verb, resource]
        args += ["-n", namespace] if namespace else ["--all-namespaces"]
        return self.oc(*args, check=False).stdout.strip() == "yes"

    # ---------- objets
    def has_runtime_class(self, name: str) -> bool:
        return self.oc("get", "runtimeclass", name, check=False).returncode == 0

    def runtime_classes(self) -> list[dict]:
        return self.get_json("get", "runtimeclass")["items"]

    def node(self, name: str) -> dict:
        return self.get_json("get", "node", name)

    def nodes(self, selector: dict | None = None) -> list[dict]:
        args = ["get", "nodes"]
        if selector:
            args += ["-l", ",".join(f"{k}={v}" for k, v in selector.items())]
        return self.get_json(*args)["items"]

    def node_problems(self, selector: dict | None) -> list[str]:
        problems = []
        nodes = self.nodes(selector)
        if not nodes:
            return [f"aucun nœud ne correspond au sélecteur {selector}"]
        for n in nodes:
            name = n["metadata"]["name"]
            for c in n["status"]["conditions"]:
                if c["type"] == "Ready" and c["status"] != "True":
                    problems.append(f"nœud {name} non Ready : {c.get('message', '')}")
                if c["type"] in PRESSURE_CONDITIONS and c["status"] == "True":
                    problems.append(f"nœud {name} en {c['type']} : {c.get('message', '')}")
            if n["spec"].get("unschedulable"):
                problems.append(f"nœud {name} cordonné (unschedulable)")
        return problems

    def fingerprint(self, runtime_classes: list[str], selector: dict | None) -> dict:
        """Tout ce qui décrit l'environnement et peut expliquer un écart entre deux campagnes."""
        nodes = []
        for n in self.nodes(selector):
            info = n["status"]["nodeInfo"]
            nodes.append({
                "name": n["metadata"]["name"],
                "arch": info["architecture"],
                "kernel": info["kernelVersion"],
                "os_image": info["osImage"],
                "container_runtime": info["containerRuntimeVersion"],
                "kubelet": info["kubeletVersion"],
                "cpu": n["status"]["capacity"].get("cpu"),
                "memory": n["status"]["capacity"].get("memory"),
            })
        rcs = {}
        for rc in runtime_classes:
            r = self.oc("get", "runtimeclass", rc, "-o", "json", check=False)
            rcs[rc] = ({k: json.loads(r.stdout).get(k) for k in ("handler", "overhead", "scheduling")}
                       if r.returncode == 0 else None)
        return {
            "platform": self.platform,
            "api_server": self.api_server(),
            "version": self.platform_version(),
            "nodes": nodes,
            "runtime_classes": rcs,
        }
