"""Valide tous les résultats bruts results/**/*.json contre schemas/result.schema.json.

Usage : uv run scripts/validate_results.py [répertoire]   (défaut : results/)
Code retour : 0 si tout est valide, 1 sinon.
"""

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent


def show(path: Path) -> str:
    """Chemin lisible : relatif au dépôt si possible, absolu sinon."""
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "results"
    schema = json.loads((ROOT / "schemas" / "result.schema.json").read_text())
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )

    files = sorted(target.rglob("*.json")) if target.exists() else []
    errors = 0
    for f in files:
        if f.name == "campaign.json":
            continue
        try:
            doc = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            print(f"KO  {show(f)} : JSON invalide ({e})")
            errors += 1
            continue
        problems = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
        # Cohérence chemin <-> contenu : results/<campagne>/<ENV>/<ID>/<runtime>/run-<n>.json
        parts = f.relative_to(target).parts
        if len(parts) >= 4 and not problems:
            env_id, test_id, runtime, _ = parts[-4:]
            for field, expected, actual in (
                ("env.id", env_id, doc["env"]["id"]),
                ("test_id", test_id, doc["test_id"]),
                ("runtime", runtime, doc["runtime"]),
            ):
                if expected != actual:
                    problems.append(f"{field}={actual!r} incohérent avec le chemin ({expected!r})")
        if problems:
            errors += 1
            print(f"KO  {show(f)}")
            for p in problems:
                msg = p if isinstance(p, str) else f"{'/'.join(map(str, p.path)) or '(racine)'} : {p.message}"
                print(f"    - {msg}")
        else:
            print(f"OK  {show(f)}")

    print(f"\n{len(files)} fichier(s), {errors} en erreur")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
