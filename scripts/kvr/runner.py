"""Planification, exécution et rejeu d'une campagne, sur une cible (OpenShift / Kubernetes, local ou distant)."""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import jsonschema
import yaml

from . import RUNNER_VERSION, anonymize, components, kyverno, registry
from .cluster import Cluster, OcError
from .context import Blocked, NotSupported, TestContext

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "tests"
SCHEMA = json.loads((REPO_ROOT / "schemas" / "result.schema.json").read_text())
VALID_STATUSES = {"PASS", "FAIL", "PARTIAL", "NOT_SUPPORTED", "BLOCKED", "N/A"}


# ---------------------------------------------------------------- configuration
def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def recorded_target(target: dict) -> dict:
    """Cible enregistrée : sans chemin local de fichier de secret."""
    tgt = copy.deepcopy(target)
    ps = tgt.get("registry", {}).get("pull_secret")
    if ps and ps.get("dockerconfigjson_file"):
        ps["dockerconfigjson_file"] = "<fichier local>"
    return tgt


def recorded_config(config: dict) -> dict:
    """Config enregistrée dans campaign.json : sans les profils des autres clusters."""
    cfg = copy.deepcopy(config)
    cfg.pop("profiles", None)
    return cfg


# ---------------------------------------------------------------- découverte des tests
@dataclass
class TestDef:
    id: str
    meta: dict
    module: ModuleType
    dir: Path


def discover_tests() -> dict[str, TestDef]:
    tests = {}
    for f in sorted(TESTS_DIR.glob("*/test.py")):
        spec = importlib.util.spec_from_file_location(f"kvr_test_{f.parent.name}", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        meta = mod.META
        if meta["id"] != f.parent.name:
            raise ValueError(f"{f} : META.id={meta['id']} ≠ nom du dossier")
        tests[meta["id"]] = TestDef(meta["id"], meta, mod, f.parent)
    return tests


def select_tests(tests: dict[str, TestDef], ids: list[str] | None, category: str | None,
                 priority: str | None) -> list[TestDef]:
    missing = set(ids or []) - set(tests)
    if missing:
        raise SystemExit(f"tests inconnus : {', '.join(sorted(missing))}")
    return [t for t in tests.values()
            if (not ids or t.id in ids)
            and (not category or t.meta["category"] == category)
            and (not priority or t.meta.get("priority") == priority)]


# ---------------------------------------------------------------- plan
def build_plan(selected: list[TestDef], config: dict, runtimes: list[str],
               runs_override: int | None, warmup: bool) -> list[dict]:
    """Plan déterministe. Ordre ABAB : runtimes alternés à chaque run pour neutraliser la dérive."""
    plan = []
    for t in selected:
        ov = config.get("overrides", {}).get(t.id, {})
        runs = runs_override or ov.get("runs") or t.meta.get("runs") or config["defaults"]["runs"]
        first = 0 if (warmup and t.meta.get("warmup", True)) else 1
        # Variantes (ex. moteurs de build DIND V1..V4) : même alternance ABAB pour chacune.
        for variant in ov.get("variants") or t.meta.get("variants") or [None]:
            for run in range(first, runs + 1):
                order = runtimes if run % 2 == 1 or run == 0 else list(reversed(runtimes))
                plan += [{"test_id": t.id, "runtime": rt, "run": run, **({"variant": variant} if variant else {})}
                         for rt in order]
    return plan


# ---------------------------------------------------------------- utilitaires
def git_state() -> dict:
    def g(*a):
        return subprocess.run(["git", *a], cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip()
    return {"git_commit": g("rev-parse", "HEAD") or "unknown",
            "git_dirty": bool(g("status", "--porcelain", "--", ".", ":!results", ":!evidence"))}


def sha256_json(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def diff_dicts(a, b, path="") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            out += diff_dicts(a.get(k), b.get(k), f"{path}.{k}" if path else k)
        return out
    return [] if a == b else [f"{path} : {a!r} → {b!r}"]


def log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------- campagne
class Campaign:
    def __init__(self, config: dict, cluster: Cluster, target: dict, plan: list[dict],
                 tests: dict[str, TestDef], allow_dirty: bool = False,
                 replay_of: dict | None = None, precheck: dict | None = None,
                 allow_destructive: bool = False, safe_mode: bool = True,
                 excluded_intrusive: list[str] | None = None) -> None:
        self.config = config
        self.safe_mode = safe_mode
        self.excluded_intrusive = excluded_intrusive or []
        # Anonymisation de tout ce qui est écrit (dépôt public). Désactivable seulement par profil
        # (`anonymize: false`), pour un cluster jetable dont les noms ne révèlent rien.
        self.anon = anonymize.Anonymizer(REPO_ROOT / ".kvr-private" / "anonymization-map.json",
                                         enabled=target.get("anonymize", True))
        self.allow_destructive = allow_destructive
        self.cluster = cluster
        self.target = target
        self.runtimes = target["runtimes"]
        self.plan = plan
        self.tests = tests
        self.precheck = precheck
        self.images = registry.resolve_images(config, target["registry"])
        self.git = git_state()
        self.replay_of = replay_of
        unknown_rt = {s["runtime"] for s in plan} - set(self.runtimes)
        if unknown_rt:
            raise SystemExit(f"runtimes inconnus : {sorted(unknown_rt)}")
        if self.git["git_dirty"] and not allow_dirty:
            raise SystemExit("arbre git modifié : commitez avant de lancer une campagne "
                             "(ou --allow-dirty, le résultat sera marqué non reproductible)")
        ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
        self.id = f"{ts}-{target['env_id']}-{self.git['git_commit'][:7]}"
        self.ns_tag = hashlib.sha256(self.id.encode()).hexdigest()[:5]
        self.results_root = REPO_ROOT / "results" / self.id
        self.evidence_root = REPO_ROOT / "evidence" / self.id / self.target["env_id"]
        self.validator = jsonschema.Draft202012Validator(SCHEMA)
        self.nodes_by_name: dict[str, dict] = {}

    # -- exécution
    def execute(self) -> int:
        rcs = [rc for rc in self.runtimes.values() if rc]
        self.fingerprint = self.cluster.fingerprint(rcs, self.target.get("node_selector"))
        self.fingerprint["kyverno"] = kyverno.detect(self.cluster)
        self.fingerprint["components"] = components.detect(self.cluster, self.target.get("node_selector"))
        self.nodes_by_name = {n["name"]: n for n in self.fingerprint["nodes"]}
        self.anon.learn_target(self.target, self.fingerprint)
        self.results_root.mkdir(parents=True, exist_ok=True)
        cfg = recorded_config(self.config)
        manifest = {
            "campaign_id": self.id,
            "runner_version": RUNNER_VERSION,
            "started_at": now_iso(),
            "command": sys.argv,
            "target": recorded_target(self.target),
            "images_resolved": self.images,
            **self.git,
            "replay_of": self.replay_of,
            "config": cfg,
            "config_sha256": sha256_json({k: v for k, v in cfg.items() if k != "operator"}),
            "plan": self.plan,
            "fingerprint": self.fingerprint,
            "precheck": self.precheck,
            "allow_destructive": self.allow_destructive,
            "safe_mode": self.safe_mode,
            "excluded_intrusive": self.excluded_intrusive,
            "anonymized": self.anon.enabled,
        }
        manifest_path = self.results_root / "campaign.json"
        self._write_manifest(manifest_path, manifest)
        log(f"\nCampagne {self.id} sur {self.target['context']} ({self.fingerprint['version']}, "
            f"{self.fingerprint['api_server']}) : {len(self.plan)} exécutions")

        summary: dict[str, int] = {}
        try:
            for i, step in enumerate(self.plan, 1):
                res = self.execute_step_guarded(step)
                summary[res["status"]] = summary.get(res["status"], 0) + 1
                tag = (f" {step['variant']}" if step.get("variant") else "") + (" (warm-up)" if step["run"] == 0 else "")
                log(f"[{i}/{len(self.plan)}] {step['test_id']:<8} {step['runtime']:<5} run {step['run']:>2}{tag} "
                    f"→ {res['status']:<13} {res['duration_s']:6.1f}s  {self._fmt(res)}")
        finally:
            manifest["finished_at"] = now_iso()
            manifest["summary"] = summary
            manifest["host_suspensions"] = self.suspensions
            manifest["public_check"] = self._public_check()
            self._write_manifest(manifest_path, manifest)
            self.anon.save()
        log(f"Résumé : {summary}\nRésultats : {self.results_root.relative_to(REPO_ROOT)}")
        if manifest["public_check"]["leaks"]:
            log(f"⚠ contrôle de publication : {len(manifest['public_check']['leaks'])} donnée(s) d'infrastructure "
                "possiblement non anonymisée(s) : uv run scripts/check_public.py " + str(self.results_root.relative_to(REPO_ROOT)))
        return 1 if summary.get("FAIL") else 0

    def _write_manifest(self, path: Path, manifest: dict) -> None:
        public = self.anon.obj(manifest)
        # La commande peut contenir le nom du contexte ou un chemin local
        public["command"] = [self.anon.text(a).replace(str(Path.home()), "~") for a in manifest["command"]]
        path.write_text(json.dumps(public, indent=2, ensure_ascii=False))

    def _public_check(self) -> dict:
        leaks = []
        for root in (self.results_root, self.evidence_root.parent):
            for f in sorted(root.rglob("*")) if root.exists() else []:
                if f.is_file() and f.stat().st_size < 20_000_000:
                    for leak in anonymize.find_leaks(f.read_text(errors="replace"), self.anon.map if self.anon.enabled else None):
                        leaks.append(f"{f.relative_to(REPO_ROOT)} : {leak}")
        return {"leaks": leaks[:200], "count": len(leaks)}

    # Veille de l'hôte (portable capot fermé, VM suspendue) : un run qui la traverse est invalide
    # (VM figée en plein test, délais faussés). Détection : écart entre horloge murale et horloge
    # monotone (qui ne compte pas la veille sur macOS). Le run est rejoué, au plus MAX_SUSPEND_RETRIES fois.
    SUSPEND_THRESHOLD_S = 30
    MAX_SUSPEND_RETRIES = 3

    def execute_step_guarded(self, step: dict) -> dict:
        if not hasattr(self, "suspensions"):
            self.suspensions = []
        for attempt in range(self.MAX_SUSPEND_RETRIES + 1):
            wall0, mono0 = time.time(), time.monotonic()
            res = self.execute_step(step)
            suspended = (time.time() - wall0) - (time.monotonic() - mono0)
            if suspended < self.SUSPEND_THRESHOLD_S:
                return res
            self.suspensions.append({**step, "suspended_s": round(suspended), "attempt": attempt})
            log(f"⚠ hôte en veille pendant {step['test_id']} {step['runtime']} run {step['run']} "
                f"({suspended:.0f} s) : run invalide, rejoué")
            if attempt == self.MAX_SUSPEND_RETRIES:
                res["observations"] += f" | ⚠ hôte en veille pendant le run ({suspended:.0f} s) : mesure non fiable"
                self._rewrite_result(step, res)
                return res
            ev = self.evidence_root / step["test_id"] / step["runtime"] / (
                f"run-{step['run']}" + (f"-{step['variant']}" if step.get("variant") else ""))
            shutil.rmtree(ev, ignore_errors=True)
        return res

    def _rewrite_result(self, step: dict, res: dict) -> None:
        vsuffix = f"-{step['variant']}" if step.get("variant") else ""
        out = self.results_root / res["env"]["id"] / step["test_id"] / step["runtime"] / f"run-{step['run']}{vsuffix}.json"
        out.write_text(json.dumps(res, indent=2, ensure_ascii=False))

    @staticmethod
    def _fmt(res: dict) -> str:
        return " ".join(f"{m['name']}={m['value']}{m['unit']}" for m in res.get("metrics", [])[:3])

    def execute_step(self, step: dict) -> dict:
        t = self.tests[step["test_id"]]
        rt, run = step["runtime"], step["run"]
        rc_name = self.runtimes[rt]
        ov = self.config.get("overrides", {}).get(t.id, {})
        params = {**t.meta.get("params", {}), **ov.get("params", {})}
        variant = step.get("variant")
        vtag = f"-{variant.split('-')[0].lower()}" if variant else ""
        vsuffix = f"-{variant}" if variant else ""
        ns = f"{self.config['defaults']['namespace_prefix']}-{self.ns_tag}-{t.id.lower()}-{rt}{vtag}-{run}"
        ctx = TestContext(cluster=self.cluster, repo_root=REPO_ROOT, test_dir=t.dir, test_id=t.id,
                          runtime=rt, runtime_class=rc_name, namespace=ns, run=run,
                          images=self.images, params=params,
                          evidence_dir=self.evidence_root / t.id / rt / f"run-{run}{vsuffix}",
                          node_selector=self.target.get("node_selector"))
        ctx.kyverno = self.fingerprint.get("kyverno")
        ctx.kata_runtime_class = self.runtimes.get("kata")
        ctx.allow_destructive = self.allow_destructive
        ctx.anonymizer = self.anon
        ctx.variant = variant
        started, t0 = now_iso(), time.perf_counter()
        status, node_name = "FAIL", None
        try:
            if rc_name and not self.cluster.has_runtime_class(rc_name):
                raise Blocked(f"RuntimeClass '{rc_name}' absente du cluster")
            self._create_namespace(ns)
            status = t.module.run(ctx)
            if status not in VALID_STATUSES:
                raise ValueError(f"statut invalide retourné par le test : {status!r}")
        except Blocked as e:
            status = "BLOCKED"
            ctx.observe(f"BLOQUÉ : {e}")
        except NotSupported as e:
            status = "NOT_SUPPORTED"
            ctx.observe(f"NON SUPPORTÉ : {e}")
        except AssertionError as e:
            status = "FAIL"
            ctx.observe(f"ÉCHEC : {e}")
        except Exception as e:  # erreur d'infrastructure ou bug du test : visible, jamais silencieuse
            status = "FAIL"
            ctx.observe(f"ERREUR : {type(e).__name__}: {e}")
            ctx.evidence("traceback.txt", traceback.format_exc().replace(str(REPO_ROOT), "<repo>")
                         .replace(str(Path.home()), "~"))
        finally:
            node_name = self._collect_and_cleanup(ctx)
        duration = round(time.perf_counter() - t0, 3)
        return self._write_result(t, ctx, step, status, started, duration, node_name)

    def _create_namespace(self, ns: str) -> None:
        self.cluster.oc("create", "ns", ns)
        # Même politique d'admission pour runc et kata. Sur OpenShift, les SCC restent le contrôle effectif.
        labels = ["kvr/managed=true", f"kvr/campaign={self.ns_tag}",
                  "pod-security.kubernetes.io/enforce=privileged",
                  "pod-security.kubernetes.io/audit=privileged",
                  "pod-security.kubernetes.io/warn=privileged"]
        if self.cluster.is_openshift:
            labels.append("security.openshift.io/scc.podSecurityLabelSync=false")
        self.cluster.oc("label", "ns", ns, "--overwrite", *labels)
        registry.install_pull_secret(self.cluster, ns, self.target["registry"])

    def _collect_and_cleanup(self, ctx: TestContext) -> str | None:
        """Collecte les preuves, supprime les pods (attente = ressources libérées avant l'exécution
        suivante), puis le namespace en asynchrone (noms uniques par campagne : pas de collision)."""
        if self.cluster.oc("get", "ns", ctx.namespace, check=False).returncode != 0:
            return None
        node_name = None
        r = self.cluster.oc("get", "pods", "-n", ctx.namespace, "-o", "json", check=False)
        if r.returncode == 0:
            pods = json.loads(r.stdout)["items"]
            if pods:
                ctx.evidence("pods.json", r.stdout)
                node_name = next((p["spec"].get("nodeName") for p in pods if p["spec"].get("nodeName")), None)
        r = self.cluster.oc("get", "events", "-n", ctx.namespace, "--sort-by=.lastTimestamp", check=False)
        if r.returncode == 0 and r.stdout.strip():
            ctx.evidence("events.txt", r.stdout)
        timeout = self.config["defaults"]["cleanup_timeout_s"]
        try:
            self.cluster.oc("delete", "pods", "--all", "-n", ctx.namespace, "--wait=true",
                            f"--timeout={timeout}s", timeout=timeout + 30)
        except OcError as e:
            ctx.observe(f"nettoyage incomplet : {e}")
        self.cluster.oc("delete", "ns", ctx.namespace, "--wait=false", check=False)
        return node_name

    def _write_result(self, t: TestDef, ctx: TestContext, step: dict, status: str,
                      started: str, duration: float, node_name: str | None) -> dict:
        node = self.nodes_by_name.get(node_name or "") or (
            self._node_summary(node_name) if node_name else self.fingerprint["nodes"][0])
        rc_info = self.fingerprint["runtime_classes"].get(ctx.runtime_class or "")
        env = {
            "id": self.target["env_id"],
            "context": self.anon.text(self.target["context"]),
            "platform": self.fingerprint["version"],
            "arch": node["arch"],
            "node": self.anon.text(node["name"]),
            "nested_virt": bool(self.target.get("nested_virt")),
            "container_runtime": node["container_runtime"],
        }
        if ctx.runtime_class:
            kata_info = self.fingerprint.get("components", {}).get("kata")
            kata_info = kata_info if isinstance(kata_info, dict) else {}
            rc_detail = kata_info.get("runtime_classes", {}).get(ctx.runtime_class, {})
            detected = kata_info.get("version", "inconnue")
            env["kata_version"] = (f"{kata_info.get('install', 'inconnue')} {detected}"
                                   if detected != "inconnue" else self.target.get("kata_version") or "inconnue")
            env["kata_runtime_class"] = ctx.runtime_class
            env["kata_shim"] = rc_detail.get("shim", "inconnu")
            if rc_info:
                env["hypervisor"] = rc_info["handler"]
        res = {
            "schema_version": "1.0",
            "test_id": t.id,
            "category": t.meta["category"],
            "title": t.meta["title"],
            "runtime": ctx.runtime,
            "run": step["run"],
            "warmup": step["run"] == 0,
            "campaign": {"id": self.id, **self.git, "replay_of": (self.replay_of or {}).get("campaign_id")},
            "env": env,
            "started_at": started,
            "duration_s": duration,
            "status": status,
            "metrics": ctx.metrics,
            "observations": self.anon.text(" | ".join(ctx.observations)),
            "evidence": ctx.evidence_files,
        }
        for k in ("aspect", "variant", "ci_platform", "agent_mode"):
            if k in t.meta:
                res[k] = t.meta[k]
        if step.get("variant"):
            res["variant"] = step["variant"]
        if ctx.manifest_sha256:
            res["manifest_sha256"] = ctx.manifest_sha256
        if self.config.get("operator"):
            res["operator"] = self.config["operator"]
        errors = [e.message for e in self.validator.iter_errors(res)]
        if errors:
            raise RuntimeError(f"résultat non conforme au schéma ({t.id}/{ctx.runtime}/{step['run']}) : {errors}")
        vsuffix = f"-{step['variant']}" if step.get("variant") else ""
        out = self.results_root / env["id"] / t.id / ctx.runtime / f"run-{step['run']}{vsuffix}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=2, ensure_ascii=False))
        return res

    def _node_summary(self, name: str) -> dict:
        info = self.cluster.node(name)["status"]["nodeInfo"]
        summary = {"name": name, "arch": info["architecture"], "container_runtime": info["containerRuntimeVersion"]}
        self.nodes_by_name[name] = summary
        return summary


# ---------------------------------------------------------------- rejeu
def load_replay(campaign_json: Path) -> dict:
    """Campagne d'origine : config (images, paramètres, surcharges), plan et cible enregistrés."""
    old = json.loads(campaign_json.read_text())
    for key in ("config", "plan", "target", "fingerprint", "git_commit"):
        if key not in old:
            raise SystemExit(f"{campaign_json} : clé '{key}' absente, fichier de campagne invalide")
    return old


def replay_diffs(old: dict, cluster: Cluster, target: dict) -> list[str]:
    """Écarts entre la campagne d'origine et l'exécution à venir (code, cluster, environnement)."""
    diffs = []
    cur_git = git_state()
    if cur_git["git_commit"] != old["git_commit"]:
        diffs.append(f"git_commit : {old['git_commit'][:7]} → {cur_git['git_commit'][:7]} "
                     "(code des tests potentiellement différent)")
    if old.get("git_dirty"):
        diffs.append("la campagne d'origine a été lancée sur un arbre git modifié")
    if old["target"]["api_server"] != target["api_server"]:
        diffs.append(f"cluster : {old['target']['api_server']} → {target['api_server']}")
    rcs = [rc for rc in target["runtimes"].values() if rc]
    current = cluster.fingerprint(rcs, target.get("node_selector"))
    current["kyverno"] = kyverno.detect(cluster)
    diffs += [f"environnement : {d}" for d in diff_dicts(old["fingerprint"], current)]
    return diffs
