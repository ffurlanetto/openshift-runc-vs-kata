"""Contrôle de publication : rien d'identifiant l'infrastructure ne doit entrer dans le dépôt (public).

    uv run scripts/check_public.py                 # fichiers indexés (git add) : usage en hook pre-commit
    uv run scripts/check_public.py results/<c> evidence/<c>   # dossiers ou fichiers donnés
    uv run scripts/check_public.py --fix results/<c> evidence/<c>
        # anonymise en place (campagnes produites avant l'anonymisation automatique) : les valeurs
        # de la cible sont lues dans results/<c>/campaign.json, la table locale est complétée

Code de sortie 1 si une fuite possible subsiste. Installer en hook :
    printf '#!/bin/sh\nexec uv run scripts/check_public.py\n' > .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kvr.anonymize import Anonymizer, find_leaks  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / ".kvr-private" / "anonymization-map.json"
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".lock", ".svg"}
# Fichiers du banc qui citent volontairement des exemples d'adresses ou de domaines (code, documentation).
SKIP_PREFIXES = ("scripts/", "tests/", "schemas/", "policies/", "setup-values/", "uv.lock")


def files_from(args_paths: list[str]) -> list[Path]:
    if not args_paths:
        out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], cwd=ROOT,
                             capture_output=True, text=True).stdout.split()
        return [ROOT / p for p in out if not p.startswith(SKIP_PREFIXES)]
    files = []
    for p in args_paths:
        path = (ROOT / p) if not Path(p).is_absolute() else Path(p)
        files += [f for f in path.rglob("*") if f.is_file()] if path.is_dir() else [path]
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--fix", action="store_true", help="anonymise les fichiers en place")
    args = ap.parse_args()
    anon = Anonymizer(MAP)
    if args.fix:
        for p in args.paths:
            cj = ROOT / p / "campaign.json"
            if cj.exists():
                c = json.loads(cj.read_text())
                anon.learn_target(c.get("target", {}), c.get("fingerprint", {}))
    leaks: list[str] = []
    fixed = 0
    for f in files_from(args.paths):
        if f.suffix.lower() in SKIP_SUFFIXES or not f.exists():
            continue
        try:
            text = f.read_text()
        except UnicodeDecodeError:
            continue
        if args.fix:
            new = anon.text(text)
            if f.name == "campaign.json" or f.suffix == ".json":
                try:
                    new = json.dumps(anon.obj(json.loads(text)), indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    pass
            if new != text:
                f.write_text(new)
                fixed += 1
            text = new
        leaks += [f"{f.relative_to(ROOT)} : {leak}" for leak in find_leaks(text, anon.map)]
    if args.fix:
        anon.save()
        print(f"{fixed} fichier(s) anonymisé(s) ; table locale : {MAP.relative_to(ROOT)} (ne jamais la commiter)")
    for leak in leaks[:100]:
        print(f"FUITE POSSIBLE  {leak}")
    if len(leaks) > 100:
        print(f"… {len(leaks) - 100} autres")
    print("OK : aucune donnée d'infrastructure détectée" if not leaks else
          f"{len(leaks)} fuite(s) possible(s) : anonymiser (--fix) ou retirer avant commit")
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(main())
