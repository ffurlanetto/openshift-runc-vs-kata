"""Préparation des composants du banc sur un cluster de TEST (jamais sur un cluster partagé sans accord).

  ./setup kyverno [--context X]     installe Kyverno (chart épinglé dans campaign.yaml, miroir appliqué)

Ne réinstalle pas un composant déjà présent : sur les clusters distants, l'existant est utilisé tel quel.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kvr import kyverno  # noqa: E402
from kvr.registry import resolve_charts  # noqa: E402
from kvr.runner import REPO_ROOT, load_config  # noqa: E402
from kvr.target import build_target, choose_context, confirm  # noqa: E402


def setup_kyverno(config: dict, args) -> int:
    ctx_entry = choose_context(args.context)
    cluster, target = build_target(config, ctx_entry, env_id="setup")
    existing = kyverno.detect(cluster)
    if existing:
        print(f"Kyverno déjà présent (version {existing['version']}, ns {existing['namespace']}) : rien à faire.")
        return 0
    if not shutil.which("helm"):
        raise SystemExit("helm introuvable (requis pour ./setup)")
    chart = resolve_charts(config, target["registry"])["kyverno"]
    confirm(target, cluster.platform_version(), args.yes)
    cmd = ["helm", "upgrade", "--install", "kyverno", chart["ref"], "--version", str(chart["version"]),
           "--kube-context", ctx_entry["name"], "--namespace", "kyverno", "--create-namespace",
           "--wait", "--timeout", "10m"]
    print("→ " + " ".join(cmd))
    rc = subprocess.run(cmd).returncode
    if rc == 0:
        print(f"Kyverno installé : {kyverno.detect(cluster)}")
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("component", choices=["kyverno"])
    ap.add_argument("--context")
    ap.add_argument("--yes", "-y", action="store_true")
    ap.add_argument("--config", default=str(REPO_ROOT / "campaign.yaml"))
    args = ap.parse_args()
    config = load_config(Path(args.config))
    return {"kyverno": setup_kyverno}[args.component](config, args)


if __name__ == "__main__":
    sys.exit(main())
