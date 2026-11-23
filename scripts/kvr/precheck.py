"""Contrôle des prérequis d'une campagne : outils, accès, droits, cluster, registre/miroir, Kyverno,
admission, pull des images et smoke test par runtime."""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from . import kyverno, registry
from .cluster import Cluster, OcError
from .context import TestContext

OK, WARN, KO, INFO = "OK", "WARN", "KO", "INFO"
ICON = {OK: "\033[32m✔\033[0m", WARN: "\033[33m▲\033[0m", KO: "\033[31m✘\033[0m", INFO: "\033[36mi\033[0m"}

# Droits nécessaires (verbe, ressource), vérifiés avec `kubectl auth can-i` sur tous les namespaces.
RBAC_COMMON = [
    ("create", "namespaces"), ("delete", "namespaces"), ("patch", "namespaces"),
    ("create", "pods"), ("delete", "pods"), ("get", "pods"), ("create", "pods/exec"),
    ("list", "events"), ("list", "nodes"), ("list", "runtimeclasses.node.k8s.io"),
]
RBAC_OPENSHIFT = [
    ("get", "clusterversions.config.openshift.io"),
    ("create", "rolebindings.rbac.authorization.k8s.io"),
    ("use", "securitycontextconstraints.security.openshift.io/privileged"),
    ("use", "securitycontextconstraints.security.openshift.io/hostnetwork-v2"),
]
RBAC_PULL_SECRET = [("create", "secrets"), ("patch", "serviceaccounts")]
RBAC_POL = {"cel": [("create", "namespacedvalidatingpolicies.policies.kyverno.io"),
                    ("create", "namespacedmutatingpolicies.policies.kyverno.io"),
                    ("create", "pods/ephemeralcontainers"), ("patch", "pods/ephemeralcontainers")],
            "legacy": [("create", "policies.kyverno.io"),
                       ("create", "pods/ephemeralcontainers"), ("patch", "pods/ephemeralcontainers")]}
PHASE_CRDS = {"AGT": ["sandboxes.agents.x-k8s.io", "sandboxtemplates.extensions.agents.x-k8s.io"]}
PHASE_TOOLS = {"DIND": ["helm"], "AGT": ["helm"]}
PULL_ERRORS = {"ErrImagePull", "ImagePullBackOff", "InvalidImageName", "ErrImageNeverPull",
               "RegistryUnavailable", "SignatureValidationFailed"}


@dataclass
class Check:
    level: str
    area: str
    name: str
    detail: str = ""
    hint: str = ""


class Precheck:
    def __init__(self, repo_root: Path, config: dict, cluster: Cluster, target: dict,
                 phases: list[str], runtimes: list[str], smoke: bool) -> None:
        self.repo_root = repo_root
        self.config = config
        self.cluster = cluster
        self.target = target
        self.phases = phases
        self.runtimes = runtimes
        self.smoke = smoke
        self.images = registry.resolve_images(config, target["registry"])
        self.kyverno: dict | None = None
        self.checks: list[Check] = []

    def add(self, level: str, area: str, name: str, detail: str = "", hint: str = "") -> None:
        self.checks.append(Check(level, area, name, detail, hint))
        print(f"  {ICON[level]} {area:<9} {name:<40} {detail}")
        if hint and level in (WARN, KO):
            print(f"      → {hint}")

    @property
    def ok(self) -> bool:
        return not any(c.level == KO for c in self.checks)

    # ------------------------------------------------------------------ orchestrateur
    def run(self) -> bool:
        print("\nPrécheck")
        self._safe("local", self.check_local)
        if not self._safe("cluster", self.check_access):
            return self._summary()
        if not self._safe("droits", self.check_rbac):
            self.add(INFO, "cluster", "contrôles du cluster", "non lancés : droits insuffisants")
            return self._summary()
        for area, check in (("nœuds", self.check_nodes), ("runtimes", self.check_runtimes),
                            ("registre", self.check_registry_config), ("kyverno", self.check_kyverno),
                            ("phases", self.check_phases), ("cluster", self.check_misc)):
            self._safe(area, check)
        if self.smoke and not self.ok:
            self.add(INFO, "smoke", "contrôles dans le cluster", "non lancés : corriger d'abord les bloquants")
        elif self.smoke:
            self.check_in_cluster()
        return self._summary()

    def _safe(self, area: str, check) -> bool:
        """Exécute un contrôle ; une exception devient un KO lisible au lieu d'interrompre le precheck."""
        before = sum(c.level == KO for c in self.checks)
        try:
            result = check()
        except Exception as e:  # noqa: BLE001 : le precheck doit toujours rendre un bilan
            self.add(KO, area, check.__name__.removeprefix("check_"), f"erreur : {str(e)[:200]}")
            return False
        if result is False:
            return False
        return sum(c.level == KO for c in self.checks) == before

    def _summary(self) -> bool:
        n = {lvl: sum(c.level == lvl for c in self.checks) for lvl in (OK, WARN, KO)}
        print(f"\n  Bilan : {n[OK]} OK, {n[WARN]} avertissement(s), {n[KO]} bloquant(s)")
        return self.ok

    # ------------------------------------------------------------------ local
    def check_local(self) -> None:
        r = subprocess.run([self.cluster.kubectl, "version", "--client", "-o", "json"],
                           capture_output=True, text=True)
        client = json.loads(r.stdout)["clientVersion"]["gitVersion"] if r.returncode == 0 else "?"
        self.add(OK, "local", "kubectl", client)
        git = subprocess.run(["git", "status", "--porcelain"], cwd=self.repo_root, capture_output=True, text=True)
        if git.returncode != 0:
            self.add(WARN, "local", "dépôt git", "non disponible", "les résultats ne seront pas liés à un commit")
        elif git.stdout.strip():
            self.add(WARN, "local", "dépôt git", "modifications non commitées",
                     "commiter avant ./run (sinon --allow-dirty, résultats marqués non reproductibles)")
        else:
            self.add(OK, "local", "dépôt git", "propre")
        allowed = set(self.config.get("unpinned_images_allowed") or [])
        unpinned = [k for k, v in self.config["images"].items() if "@sha256:" not in v and k not in allowed]
        if unpinned:
            self.add(KO, "local", "images épinglées par digest", f"non épinglées : {unpinned}",
                     "remplacer les tags par des digests dans campaign.yaml")
        else:
            self.add(OK, "local", "images épinglées par digest", f"{len(self.config['images'])} image(s)")
        if os.environ.get("KVR_PYPI_INDEX"):
            self.add(INFO, "local", "dépendances Python", f"miroir {os.environ['KVR_PYPI_INDEX']}")
        for phase, tools in PHASE_TOOLS.items():
            if phase in self.phases:
                for tool in tools:
                    if shutil.which(tool):
                        self.add(OK, "local", f"{tool} (phase {phase})", "présent")
                    else:
                        self.add(WARN, "local", f"{tool} (phase {phase})", "absent",
                                 f"nécessaire pour préparer la phase {phase} (installation des composants)")

    # ------------------------------------------------------------------ accès
    def check_access(self) -> bool:
        try:
            version = self.cluster.platform_version()
        except OcError as e:
            self.add(KO, "cluster", "connexion API", str(e)[:150],
                     "vérifier le contexte, le VPN/proxy, la validité du token (kubectl get ns)")
            return False
        self.add(OK, "cluster", "connexion API", self.target["api_server"])
        self.add(INFO, "cluster", "plateforme", version)
        try:
            client = json.loads(subprocess.run([self.cluster.kubectl, "version", "--client", "-o", "json"],
                                               capture_output=True, text=True).stdout)["clientVersion"]
            server = self.cluster.server_version()
            cminor = int(re.sub(r"\D", "", client["minor"]))
            sminor = int(re.search(r"v\d+\.(\d+)", server).group(1))
            level = WARN if abs(cminor - sminor) > 1 else OK
            self.add(level, "cluster", "écart de version kubectl", f"client 1.{cminor} / serveur 1.{sminor}",
                     "kubectl supporte ±1 version mineure : installer un client adapté")
        except (OcError, AttributeError, ValueError, KeyError) as e:
            self.add(WARN, "cluster", "écart de version kubectl", f"indéterminé ({e})")
        return True

    def check_rbac(self) -> None:
        wanted = list(RBAC_COMMON)
        if self.cluster.is_openshift:
            wanted += RBAC_OPENSHIFT
        if self.target["registry"].get("pull_secret"):
            wanted += RBAC_PULL_SECRET
        missing = [f"{v} {r}" for v, r in wanted if not self.cluster.can_i(v, r)]
        if missing:
            self.add(KO, "droits", "RBAC / SCC", f"manquants : {', '.join(missing)}",
                     "utiliser un compte dédié au banc avec ces droits (cluster-admin sur un cluster de test)")
        else:
            self.add(OK, "droits", "RBAC / SCC", f"{len(wanted)} droits vérifiés")

    # ------------------------------------------------------------------ nœuds et runtimes
    def check_nodes(self) -> None:
        sel = self.target.get("node_selector") or None
        nodes = self.cluster.nodes(sel)
        archs = sorted({n["status"]["nodeInfo"]["architecture"] for n in nodes})
        self.add(INFO if nodes else KO, "nœuds", "nœuds de bench",
                 f"{len(nodes)} nœud(s), arch {archs}, sélecteur {sel or 'aucun'}")
        problems = self.cluster.node_problems(sel)
        for p in problems:
            hint = ""
            if "DiskPressure" in p:
                hint = "libérer de l'espace (images inutilisées) ou agrandir le disque (CRC : crc config set disk-size)"
            elif "MemoryPressure" in p:
                hint = "libérer de la mémoire ou en ajouter au nœud"
            self.add(KO, "nœuds", "état", p, hint)
        if nodes and not problems:
            self.add(OK, "nœuds", "état", "Ready, sans pression ressources, planifiables")

    def check_runtimes(self) -> None:
        rc = self.target["runtimes"]["kata"]
        if "kata" not in self.runtimes:
            self.add(INFO, "runtimes", "kata", "non sélectionné")
            return
        r = self.cluster.oc("get", "runtimeclass", rc, "-o", "json", check=False)
        if r.returncode != 0:
            self.add(KO, "runtimes", f"RuntimeClass {rc}", "absente",
                     "installer Kata (OSC + KataConfig, ou kata-deploy), ou lancer avec --runtimes runc")
            return
        obj = json.loads(r.stdout)
        overhead = (obj.get("overhead") or {}).get("podFixed", {})
        self.add(OK, "runtimes", f"RuntimeClass {rc}", f"handler={obj['handler']} overhead={overhead or 'aucun'}")
        sched = (obj.get("scheduling") or {}).get("nodeSelector")
        if sched:
            self.add(INFO, "runtimes", "placement kata", f"nodeSelector={sched}")

    # ------------------------------------------------------------------ registre / miroir
    def check_registry_config(self) -> None:
        reg = self.target["registry"]
        if reg["mirrors"]:
            self.add(INFO, "registre", "réécriture miroir", ", ".join(f"{m['from']}→{m['to']}" for m in reg["mirrors"]))
        else:
            self.add(INFO, "registre", "réécriture miroir", "aucune (pull direct, ou miroir géré par le cluster)")
        ps = reg.get("pull_secret")
        if not ps:
            return
        if ps.get("from_namespace"):
            src = ps.get("source_name", ps["name"])
            ok = self.cluster.oc("get", "secret", src, "-n", ps["from_namespace"], check=False).returncode == 0
            self.add(OK if ok else KO, "registre", "secret de pull (source)", f"{ps['from_namespace']}/{src}",
                     "créer le secret source, ou utiliser dockerconfigjson_file")
        elif ps.get("dockerconfigjson_file"):
            path = Path(os.path.expanduser(ps["dockerconfigjson_file"]))
            self.add(OK if path.exists() else KO, "registre", "secret de pull (fichier)", str(path),
                     "fichier dockerconfigjson introuvable")

    # ------------------------------------------------------------------ Kyverno
    def check_kyverno(self) -> None:
        self.kyverno = kyverno.detect(self.cluster)
        wanted = "POL" in self.phases
        if not self.kyverno:
            level = KO if wanted else INFO
            self.add(level, "kyverno", "présence", "absent",
                     "./setup kyverno (cluster de test) ou exclure la phase : --skip POL")
            return
        k = self.kyverno
        self.add(OK, "kyverno", "présence",
                 f"version {k['version']} (ns {k['namespace']}), API {k['flavor']} {k['api_version']}")
        if k["enforce_cluster_policies"]:
            self.add(WARN, "kyverno", "policies cluster en Enforce",
                     f"{len(k['enforce_cluster_policies'])} : {', '.join(k['enforce_cluster_policies'][:6])}",
                     "elles s'appliquent aussi aux pods de test : voir le contrôle d'admission ci-dessous")
        else:
            self.add(OK, "kyverno", "policies cluster en Enforce", "aucune")
        if wanted:
            missing = [f"{v} {r}" for v, r in RBAC_POL[k["flavor"]] if not self.cluster.can_i(v, r)]
            self.add(KO if missing else OK, "droits", "phase POL", f"manquants : {missing}" if missing else "OK",
                     "droits de création des policies Kyverno namespacées")

    def check_phases(self) -> None:
        self.add(INFO, "phases", "sélection", ", ".join(self.phases))
        for phase, crds in PHASE_CRDS.items():
            if phase not in self.phases:
                continue
            absent = [c for c in crds if self.cluster.oc("get", "crd", c, check=False).returncode != 0]
            if absent:
                self.add(WARN, "phases", f"{phase} : CRD", f"absentes : {absent}",
                         "installer Agent Sandbox (agent-sandbox-operator ou upstream) ; sinon tests AGT BLOCKED")
            else:
                self.add(OK, "phases", f"{phase} : CRD", "présentes")

    def check_misc(self) -> None:
        r = self.cluster.oc("get", "--raw", "/apis/metrics.k8s.io/v1beta1/nodes", check=False)
        self.add(OK if r.returncode == 0 else WARN, "cluster", "Metrics API",
                 "disponible" if r.returncode == 0 else "indisponible",
                 "nécessaire pour l'overhead (PERF/OPS). CRC : crc config set enable-cluster-monitoring true")
        r = self.cluster.oc("get", "apiservices", "-o", "json", check=False)
        if r.returncode == 0:
            broken = [a["metadata"]["name"] for a in json.loads(r.stdout)["items"]
                      if any(c["type"] == "Available" and c["status"] != "True"
                             for c in a.get("status", {}).get("conditions", []))]
            self.add(WARN if broken else OK, "cluster", "APIServices indisponibles",
                     ", ".join(broken) if broken else "aucune",
                     "une APIService en panne bloque la suppression des namespaces (Terminating) : "
                     "réparer le service concerné")
        r = self.cluster.oc("get", "ns", "-l", "kvr/managed=true", "-o", "name", check=False)
        left = r.stdout.split()
        self.add(WARN if left else OK, "cluster", "namespaces résiduels",
                 f"{len(left)} namespace(s) du banc" if left else "aucun", "./run --cleanup")

    # ------------------------------------------------------------------ contrôles dans le cluster
    def check_in_cluster(self) -> None:
        """Namespace éphémère : admission (dry-run), pull de chaque image, pod réel par runtime."""
        ns = f"{self.config['defaults']['namespace_prefix']}-precheck-{secrets.token_hex(3)}"
        try:
            self.cluster.oc("create", "ns", ns)
            labels = ["kvr/managed=true", "pod-security.kubernetes.io/enforce=privileged"]
            if self.cluster.is_openshift:
                labels.append("security.openshift.io/scc.podSecurityLabelSync=false")
            self.cluster.oc("label", "ns", ns, "--overwrite", *labels)
            registry.install_pull_secret(self.cluster, ns, self.target["registry"])
        except OcError as e:
            self.add(KO, "smoke", "namespace de test", str(e)[:200])
            return
        try:
            self.check_admission(ns)
            self.check_image_pulls(ns)
            self.check_smoke_pods(ns)
        finally:
            self.cluster.oc("delete", "ns", ns, "--wait=false", check=False)

    def _ctx(self, ns: str, runtime: str) -> TestContext:
        return TestContext(cluster=self.cluster, repo_root=self.repo_root,
                           test_dir=self.repo_root / "tests" / "_templates", test_id="PRECHECK",
                           runtime=runtime, runtime_class=self.target["runtimes"].get(runtime), namespace=ns,
                           run=0, images=self.images, params={}, evidence_dir=Path("/nonexistent"),
                           node_selector=self.target.get("node_selector"))

    def check_admission(self, ns: str) -> None:
        """Les pods du banc passent-ils l'admission existante (Kyverno, Gatekeeper, VAP, SCC, quotas) ?"""
        ctx = self._ctx(ns, "runc")
        cases = [("pod restreint (FUN/PERF/SEC)", ctx.render("probe-pod.yaml.j2"), KO),
                 ("pod bonnes pratiques (POL)", ctx.render("policy-pod.yaml.j2"), KO if "POL" in self.phases else WARN),
                 ("pod privilégié (SEC/DIND/POL-11)", ctx.render("policy-pod.yaml.j2",
                                                                  violations={"privileged": True}), WARN)]
        for label, manifest, level in cases:
            admitted, _, msg = kyverno.dry_run(self.cluster, ns, manifest)
            if admitted:
                self.add(OK, "admission", label, "admis")
            else:
                self.add(level, "admission", label, f"REFUSÉ : {msg[:160]}",
                         "une policy existante bloque les pods du banc : demander une exception pour "
                         "les namespaces kvr-* (label kvr/managed=true)")

    def check_image_pulls(self, ns: str) -> None:
        """Tire chaque image épinglée (après réécriture miroir) : pod dont la commande n'existe pas,
        pour distinguer un échec de pull d'un échec de démarrage, quelle que soit l'image."""
        allowed = set(self.config.get("unpinned_images_allowed") or [])
        pods = {}
        for key, image in self.images.items():
            if key in allowed:
                continue
            name = f"pull-{key.replace('_', '-')}"[:60]
            pod = {"apiVersion": "v1", "kind": "Pod",
                   "metadata": {"name": name, "namespace": ns},
                   "spec": {"restartPolicy": "Never", "automountServiceAccountToken": False,
                            **({"nodeSelector": self.target["node_selector"]} if self.target.get("node_selector") else {}),
                            "containers": [{"name": "pull", "image": image, "imagePullPolicy": "IfNotPresent",
                                            "command": ["/kvr-pull-check-noop"],
                                            "resources": {"requests": {"cpu": "10m", "memory": "16Mi"},
                                                          "limits": {"cpu": "50m", "memory": "32Mi"}},
                                            "securityContext": {"allowPrivilegeEscalation": False,
                                                                "capabilities": {"drop": ["ALL"]},
                                                                "runAsNonRoot": True,
                                                                **({"runAsUser": 1001} if not self.cluster.is_openshift else {}),
                                                                "seccompProfile": {"type": "RuntimeDefault"}}}]}}
            r = self.cluster.oc("create", "-f", "-", input=json.dumps(pod), check=False)
            if r.returncode != 0:
                self.add(KO, "images", key, f"pod refusé : {r.stderr.strip()[:150]}")
                continue
            pods[name] = (key, image, time.perf_counter())
        deadline = time.perf_counter() + 600
        pending = dict(pods)
        while pending and time.perf_counter() < deadline:
            for name, (key, image, t0) in list(pending.items()):
                st = json.loads(self.cluster.oc("get", "pod", name, "-n", ns, "-o", "json").stdout)["status"]
                cs = (st.get("containerStatuses") or [{}])[0]
                waiting = cs.get("state", {}).get("waiting", {})
                if waiting.get("reason") in PULL_ERRORS:
                    self.add(KO, "images", key, f"{image} : {waiting.get('reason')} {waiting.get('message', '')[:120]}",
                             "image absente du miroir, règle de réécriture ou secret de pull incorrects")
                    del pending[name]
                elif cs.get("imageID") or (waiting.get("reason") not in (None, "ContainerCreating") ) or "terminated" in cs.get("state", {}):
                    self.add(OK, "images", key, f"tirée en {time.perf_counter() - t0:.0f}s : {image[:90]}")
                    del pending[name]
            time.sleep(2)
        for name, (key, image, _) in pending.items():
            self.add(KO, "images", key, f"{image} : pull non terminé après 10 min")

    def check_smoke_pods(self, ns: str) -> None:
        """Un pod réel par runtime : démarrage, exec, noyau vu. Prouve que la chaîne complète fonctionne."""
        for rt in self.runtimes:
            rc = self.target["runtimes"].get(rt)
            if rt == "kata" and not self.cluster.has_runtime_class(rc):
                continue  # déjà signalé
            ctx = self._ctx(ns, rt)
            name = f"smoke-{rt}"
            try:
                self.cluster.oc("create", "-n", ns, "-f", "-", input=ctx.render("probe-pod.yaml.j2", name=name))
                t0 = time.perf_counter()
                ctx.wait(f"pod/{name}", timeout_s=300)
                elapsed = time.perf_counter() - t0
                rc_exec, out, err = ctx.exec(name, ["uname", "-r"])
                if rc_exec != 0:
                    raise OcError(f"exec : {err.strip()}")
                self.add(OK, "smoke", f"pod {rt}", f"Ready en {elapsed:.1f}s, noyau {out.strip()}")
            except Exception as e:  # noqa: BLE001 : diagnostic, quel que soit l'échec
                self.add(KO, "smoke", f"pod {rt}", str(e)[:200],
                         f"kubectl describe pod {name} -n {ns}")

    def report(self) -> dict:
        return {"ok": self.ok, "kyverno": self.kyverno, "images": self.images,
                "checks": [asdict(c) for c in self.checks]}
