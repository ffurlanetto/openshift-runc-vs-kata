"""Contexte fourni à chaque test : rendu des manifestes, application, attente, exec, métriques, preuves."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import jinja2

from .cluster import Cluster, OcError


class Blocked(Exception):
    """Le test ne peut pas s'exécuter (prérequis d'environnement manquant)."""


class NotSupported(Exception):
    """Le runtime ne supporte pas la fonctionnalité testée (limite constatée)."""


class TestContext:
    def __init__(self, *, cluster: Cluster, repo_root: Path, test_dir: Path, test_id: str,
                 runtime: str, runtime_class: str | None, namespace: str, run: int,
                 images: dict, params: dict, evidence_dir: Path,
                 node_selector: dict | None = None) -> None:
        self.cluster = cluster
        self.repo_root = repo_root
        self.test_dir = test_dir
        self.test_id = test_id
        self.runtime = runtime
        self.runtime_class = runtime_class
        self.namespace = namespace
        self.run = run
        self.images = images
        self.params = params
        self.evidence_dir = evidence_dir
        self.node_selector = node_selector or {}
        self.platform = cluster.platform
        self.kyverno: dict | None = None            # renseigné par le runner (détection)
        self.kata_runtime_class: str | None = None  # RuntimeClass Kata de la cible
        self.metrics: list[dict] = []
        self.observations: list[str] = []
        self.evidence_files: list[str] = []
        self._canonical_manifests: list[str] = []
        self._jinja = jinja2.Environment(
            loader=jinja2.FileSystemLoader([str(test_dir), str(test_dir.parent / "_templates")]),
            undefined=jinja2.StrictUndefined, keep_trailing_newline=True,
        )

    # ---------- manifestes ----------
    def _render(self, template: str, namespace: str, runtime_class: str | None, **extra) -> str:
        return self._jinja.get_template(template).render(
            namespace=namespace, runtime_class=runtime_class, platform=self.platform,
            node_selector=self.node_selector, images=self.images, params=self.params, **extra)

    def render(self, template: str, **extra) -> str:
        return self._render(template, self.namespace, self.runtime_class, **extra)

    def apply_template(self, template: str, verb: str = "create", **extra) -> str:
        """Rend, archive et applique un manifeste. Retourne le texte appliqué.

        Le hash `manifest_sha256` est calculé sur une forme canonique (namespace et
        runtimeClass neutralisés) : runc et kata ont le même hash si et seulement si
        leurs manifestes ne diffèrent que par le runtime.
        """
        text = self.render(template, **extra)
        self._canonical_manifests.append(self._render(template, "__NS__", None, **extra))
        self.evidence(f"manifest-{len(self._canonical_manifests)}-{Path(template).stem}", text)
        self.cluster.oc(verb, "-n", self.namespace, "-f", "-", input=text)
        return text

    def render_record(self, template: str, label: str, **extra) -> str:
        """Rend un manifeste sans l'appliquer (dry-run), en l'archivant et en l'intégrant au hash."""
        text = self.render(template, **extra)
        self._canonical_manifests.append(self._render(template, "__NS__", None, **extra))
        self.evidence(f"manifest-{len(self._canonical_manifests)}-{label}.yaml", text)
        return text

    @property
    def manifest_sha256(self) -> str | None:
        if not self._canonical_manifests:
            return None
        return hashlib.sha256("\n---\n".join(self._canonical_manifests).encode()).hexdigest()

    # ---------- cluster ----------
    def oc(self, *args: str, **kw):
        return self.cluster.oc(*args, **kw)

    def get(self, ref: str) -> dict:
        return self.cluster.get_json("get", ref, "-n", self.namespace)

    def wait(self, ref: str, condition: str = "condition=Ready", timeout_s: int = 180) -> float:
        """Attend une condition (oc wait, basé sur un watch). Retourne la durée en secondes.

        En cas d'échec sur un pod non planifiable, lève Blocked (problème d'environnement)
        plutôt qu'un échec du test.
        """
        t0 = time.perf_counter()
        try:
            self.cluster.oc("wait", ref, f"--for={condition}", f"--timeout={timeout_s}s",
                            "-n", self.namespace, timeout=timeout_s + 30)
        except OcError:
            if ref.startswith("pod/"):
                self._raise_if_unschedulable(ref.removeprefix("pod/"))
            raise
        return time.perf_counter() - t0

    def _raise_if_unschedulable(self, pod: str) -> None:
        status = self.get(f"pod/{pod}").get("status", {})
        for c in status.get("conditions", []):
            if c["type"] == "PodScheduled" and c["status"] == "False":
                raise Blocked(f"pod/{pod} non planifiable : {c.get('message', c.get('reason'))}")

    def pod_node(self, pod: str) -> dict:
        """Objet Node sur lequel tourne le pod (clusters multi-nœuds)."""
        return self.cluster.node(self.get(f"pod/{pod}")["spec"]["nodeName"])

    def wait_terminated(self, pod: str, container: str | None = None, timeout_s: int = 180) -> dict:
        """Attend que le conteneur soit terminé (ou ait redémarré) ; retourne son containerStatus."""
        deadline = time.monotonic() + timeout_s
        unschedulable_since = None
        while time.monotonic() < deadline:
            pod_obj = self.get(f"pod/{pod}")
            sched = next((c for c in pod_obj.get("status", {}).get("conditions", [])
                          if c["type"] == "PodScheduled"), None)
            if sched and sched["status"] == "False":
                unschedulable_since = unschedulable_since or time.monotonic()
                if time.monotonic() - unschedulable_since > 30:
                    self._raise_if_unschedulable(pod)
            for cs in pod_obj.get("status", {}).get("containerStatuses", []):
                if container and cs["name"] != container:
                    continue
                if "terminated" in cs.get("state", {}) or "terminated" in cs.get("lastState", {}):
                    return cs
            time.sleep(0.5)
        raise OcError(f"pod/{pod} : conteneur non terminé après {timeout_s}s")

    def exec(self, pod: str, cmd: list[str], container: str | None = None,
             timeout_s: int = 60) -> tuple[int, str, str]:
        args = ["exec", "-n", self.namespace, pod]
        if container:
            args += ["-c", container]
        r = self.cluster.oc(*args, "--", *cmd, check=False, timeout=timeout_s)
        return r.returncode, r.stdout, r.stderr

    def grant_scc(self, scc: str, service_account: str = "default") -> None:
        """OpenShift : autorise le ServiceAccount à utiliser une SCC (RoleBinding vers la
        ClusterRole `system:openshift:scc:<scc>`, sans dépendre de `oc`).
        Kubernetes : sans objet, le namespace est déjà en Pod Security `privileged`
        (même politique pour runc et kata)."""
        if not self.cluster.is_openshift:
            return
        self.cluster.oc("create", "rolebinding", f"kvr-scc-{scc}",
                        f"--clusterrole=system:openshift:scc:{scc}",
                        f"--serviceaccount={self.namespace}:{service_account}", "-n", self.namespace)

    # ---------- résultats ----------
    def metric(self, name: str, value: float, unit: str, better: str = "lower") -> None:
        self.metrics.append({"name": name, "value": value, "unit": unit, "better": better})

    def observe(self, text: str) -> None:
        self.observations.append(text)

    def evidence(self, name: str, content: str | dict | list) -> None:
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        if not isinstance(content, str):
            content = json.dumps(content, indent=2, ensure_ascii=False)
            name = name if name.endswith(".json") else name + ".json"
        elif "." not in name:
            name += ".yaml" if name.startswith("manifest") else ".txt"
        path = self.evidence_dir / name
        path.write_text(content)
        self.evidence_files.append(str(path.relative_to(self.repo_root)))
