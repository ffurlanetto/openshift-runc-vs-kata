"""Agrégation des résultats et génération du rapport (Markdown + site statique GitHub Pages).

    uv run scripts/report.py --campaign <id> [--campaign <id> …]

Produit :
- report/donnees.md       : fiches de test générées (niveau 2 de 03-FORMAT-RAPPORT.md), une colonne par runtime
                            (runc, et chaque RuntimeClass Kata rencontrée) ;
- docs/*.html             : site statique (GitHub Pages, source « main /docs ») construit à partir de
                            report/rapport-comite.md (rédigé) et report/donnees.md (généré).

Les campagnes sont lues dans l'ordre donné : pour un même (test, variante, runtime), la dernière campagne
qui le contient l'emporte (rejeu après correction du banc). Les runs d'échauffement sont exclus.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/ffurlanetto/openshift-runc-vs-kata"
CATEGORIES = {"FUN": "Fonctionnel", "PERF": "Performance", "SEC": "Sécurité", "POL": "Policies d'admission (Kyverno)",
              "OPS": "Exploitation", "LIM": "Limites", "DIND": "CI dans Kata (DIND)", "AGT": "Agents IA",
              "VOL": "Volumes", "SCR": "Secrets"}
STATUS_ICON = {"PASS": "✅ PASS", "FAIL": "❌ FAIL", "PARTIAL": "⚠️ PARTIAL", "NOT_SUPPORTED": "⛔ NON SUPPORTÉ",
               "BLOCKED": "⏸ BLOQUÉ", "N/A": "— N/A"}


# --------------------------------------------------------------------------- agrégation

def runtime_label(d: dict) -> str:
    if d["runtime"] == "runc":
        return "runc"
    env = d.get("env", {})
    shim = env.get("kata_shim")
    return f"kata:{env.get('kata_runtime_class', 'kata')}" + (f" ({shim})" if shim else "")


def load(campaigns: list[str]) -> tuple[dict, list[dict]]:
    runs: dict[tuple, dict[str, list[dict]]] = {}
    metas = []
    for cid in campaigns:
        cdir = ROOT / "results" / cid
        metas.append(json.loads((cdir / "campaign.json").read_text()))
        per_key: dict[tuple, list[dict]] = defaultdict(list)
        for f in sorted(cdir.glob("*/*/*/*.json")):
            d = json.loads(f.read_text())
            if d.get("warmup"):
                continue
            d["_file"] = str(f.relative_to(ROOT))
            per_key[(d["test_id"], d.get("variant") or "", runtime_label(d))].append(d)
        runs.update(per_key)  # la dernière campagne l'emporte, clé par clé
    return runs, metas


def pct(values: list[float], p: float) -> float:
    v = sorted(values)
    if len(v) == 1:
        return v[0]
    k = (len(v) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def fmt(x: float) -> str:
    if abs(x) >= 100:
        return f"{x:,.0f}".replace(",", " ")
    return f"{x:.3g}".replace(".", ",")


def summarize(items: list[dict]) -> dict:
    statuses = defaultdict(int)
    metrics: dict[str, dict] = {}
    obs = []
    for d in items:
        statuses[d["status"]] += 1
        for m in d.get("metrics", []):
            e = metrics.setdefault(m["name"], {"unit": m["unit"], "better": m.get("better", "lower"), "v": []})
            e["v"].append(float(m["value"]))
        o = (d.get("observations") or "").strip()
        if o and o not in obs:
            obs.append(o)
    for e in metrics.values():
        v = e["v"]
        e.update(n=len(v), med=statistics.median(v), p5=pct(v, .05), p95=pct(v, .95))
    worst = next((s for s in ("FAIL", "NOT_SUPPORTED", "PARTIAL", "BLOCKED", "N/A", "PASS") if statuses.get(s)), "N/A")
    return {"statuses": dict(statuses), "worst": worst, "metrics": metrics, "obs": obs,
            "n": len(items), "files": sorted({str(Path(d["_file"]).parent) for d in items})}


def verdict(base: dict, other: dict) -> str:
    """Règle de 03-FORMAT-RAPPORT.md §2 : significatif si |Δ| > 5 % et intervalles [p5 ; p95] disjoints."""
    if base["med"] == 0:
        return "—"
    delta = (other["med"] - base["med"]) / abs(base["med"])
    disjoint = other["p5"] > base["p95"] or other["p95"] < base["p5"]
    if abs(delta) <= .05 or not disjoint or min(base["n"], other["n"]) < 2:
        sig = " (non significatif)" if abs(delta) > .05 else ""
        return f"≈ {delta:+.0%}{sig}".replace("%", " %")
    better = (delta < 0) == (base["better"] == "lower")
    return f"{'▲' if better else '▼'} {delta:+.0%}".replace("%", " %")


def status_cell(s: dict) -> str:
    parts = [f"{STATUS_ICON.get(k, k)} {v}/{s['n']}" if len(s["statuses"]) > 1 else STATUS_ICON.get(k, k)
             for k, v in sorted(s["statuses"].items(), key=lambda kv: -kv[1])]
    return " · ".join(parts)


def md_escape(t: str) -> str:
    return t.replace("|", "\\|").replace("\n", " ")


def build_data_md(runs: dict, metas: list[dict]) -> str:
    rts = sorted({k[2] for k in runs}, key=lambda r: (r != "runc", r))
    tests: dict[str, dict] = defaultdict(lambda: {"variants": defaultdict(dict)})
    for (tid, var, rt), items in runs.items():
        t = tests[tid]
        t["title"], t["cat"] = items[0]["title"], items[0]["category"]
        t["variants"][var][rt] = summarize(items)

    out = ["# Données : fiches de test générées", "",
           "> Généré par `scripts/report.py` à partir des résultats bruts. Ne pas éditer à la main.", "",
           "## Campagnes", "", "| Campagne | Commit | Runtimes Kata | Exécutions | Début → fin |", "|---|---|---|---|---|"]
    for m in metas:
        rcs = ", ".join(f"`{k}` → `{v.get('handler')}`" for k, v in m.get("fingerprint", {}).get("runtime_classes", {}).items())
        summ = m.get("summary") or {}
        n = sum(v for v in summ.values() if isinstance(v, int)) or "?"
        out.append(f"| [`{m['campaign_id']}`](../results/{m['campaign_id']}/campaign.json) | `{m['git_commit'][:7]}` | {rcs} "
                   f"| {n} | {m.get('started_at', '?')[:16]} → {(m.get('finished_at') or '?')[:16]} |")

    out += ["", "## Tableau de bord : statuts par domaine", "",
            "Nombre de tests (toutes variantes) dont le **pire** statut sur les runs mesurés est celui indiqué.", "",
            "| Domaine | Tests | " + " | ".join(f"{rt} PASS / PARTIAL / FAIL / NON SUPP. / BLOQUÉ" for rt in rts) + " |",
            "|---|---|" + "---|" * len(rts)]
    for cat, name in CATEGORIES.items():
        ids = [t for t in tests if tests[t]["cat"] == cat]
        if not ids:
            continue
        cells = []
        for rt in rts:
            c = defaultdict(int)
            for tid in ids:
                for var in tests[tid]["variants"].values():
                    if rt in var:
                        c[var[rt]["worst"]] += 1
            cells.append(" / ".join(str(c.get(s, 0)) for s in ("PASS", "PARTIAL", "FAIL", "NOT_SUPPORTED", "BLOCKED")))
        out.append(f"| {name} | {len(ids)} | " + " | ".join(cells) + " |")

    for cat, name in CATEGORIES.items():
        ids = sorted(t for t in tests if tests[t]["cat"] == cat)
        if not ids:
            continue
        out += ["", f"## {name}"]
        for tid in ids:
            t = tests[tid]
            out += ["", f"### {tid} — {t['title']}"]
            for var in sorted(t["variants"]):
                by_rt = t["variants"][var]
                if var:
                    out += ["", f"**Variante `{var}`**"]
                out += ["", "| | " + " | ".join(r for r in rts if r in by_rt) + " |", "|---|" + "---|" * sum(r in by_rt for r in rts)]
                present = [r for r in rts if r in by_rt]
                out.append("| Statut | " + " | ".join(status_cell(by_rt[r]) for r in present) + " |")
                names = sorted({m for r in present for m in by_rt[r]["metrics"]})
                for mname in names:
                    cells = []
                    for r in present:
                        e = by_rt[r]["metrics"].get(mname)
                        if not e:
                            cells.append("—")
                            continue
                        cell = f"{fmt(e['med'])} {e['unit']}"
                        if e["n"] > 1:
                            cell += f" <sub>p5–p95 {fmt(e['p5'])}–{fmt(e['p95'])}, n={e['n']}</sub>"
                        base = by_rt.get("runc", {}).get("metrics", {}).get(mname)
                        if r != "runc" and base and e["unit"] not in ("bool",):
                            cell += f" {verdict(base, e)}"
                        cells.append(cell)
                    out.append(f"| `{mname}` | " + " | ".join(cells) + " |")
                for r in present:
                    for o in by_rt[r]["obs"][:3]:
                        out.append(f"\n- *{r}* : {md_escape(o[:600])}")
                links = " · ".join(f"[{r}](../{by_rt[r]['files'][0]})" for r in present if by_rt[r]["files"])
                out.append(f"\nRésultats bruts : {links}")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- site

CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--muted:#5f5d57;--line:#e3e0d8;--card:#ffffff;--accent:#1f5f8b;--code:#f2efe8;
--ok:#2e7d32;--ko:#b3261e;--warn:#9a6700}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#151514;--fg:#ecebe6;--muted:#a5a39b;
--line:#33322e;--card:#1d1d1b;--accent:#7cb7e0;--code:#26251f;--ok:#81c784;--ko:#ef9a9a;--warn:#e6c35c}}
:root[data-theme="dark"]{--bg:#151514;--fg:#ecebe6;--muted:#a5a39b;--line:#33322e;--card:#1d1d1b;--accent:#7cb7e0;
--code:#26251f;--ok:#81c784;--ko:#ef9a9a;--warn:#e6c35c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",
Roboto,"Helvetica Neue",Arial,sans-serif}
header{border-bottom:1px solid var(--line);background:var(--card)}
header .in,main{max-width:1100px;margin:0 auto;padding:0 16px}
header .in{display:flex;gap:24px;align-items:center;min-height:56px;flex-wrap:wrap}
header strong{font-size:15px}
nav a{color:var(--muted);text-decoration:none;margin-right:16px;font-size:14px}
nav a.on{color:var(--fg);font-weight:600}
main{padding-top:24px;padding-bottom:64px}
h1{font-size:30px;line-height:1.2;margin:8px 0 16px}
h2{font-size:22px;margin-top:40px;padding-top:8px;border-top:1px solid var(--line)}
h3{font-size:17px;margin-top:28px}
a{color:var(--accent)}
code{background:var(--code);padding:1px 5px;border-radius:4px;font-size:.88em}
pre{background:var(--code);padding:12px;border-radius:6px;overflow-x:auto}
pre code{padding:0}
blockquote{margin:16px 0;padding:8px 16px;border-left:3px solid var(--accent);background:var(--card);color:var(--muted)}
.tw{overflow-x:auto;margin:12px 0}
table{border-collapse:collapse;font-size:14px;min-width:100%}
th,td{border:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
th{background:var(--card)}
td sub{color:var(--muted);font-size:11px;display:block}
.toc{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:8px 16px;font-size:14px}
.toc ul{margin:4px 0;padding-left:18px}
footer{color:var(--muted);font-size:13px;border-top:1px solid var(--line);padding:16px;text-align:center}
"""

PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>{css}</style></head><body>
<header><div class="in"><strong>runc vs Kata · OpenShift</strong><nav>{nav}</nav></div></header>
<main>{body}</main>
<footer>Généré par <code>scripts/report.py</code> · <a href="{repo}">dépôt</a> · {stamp}</footer>
</body></html>"""


def rewrite_links(body: str, src_dir: str, site_pages: dict[str, str]) -> str:
    def fix(m):
        href = m.group(1)
        if re.match(r"^(https?:|#|mailto:)", href):
            return m.group(0)
        path, _, frag = href.partition("#")
        resolved = str((Path(src_dir) / path).resolve().relative_to(ROOT)) if path else ""
        if resolved in site_pages:
            return f'href="{site_pages[resolved]}{"#" + frag if frag else ""}"'
        kind = "tree" if not Path(resolved).suffix else "blob"
        return f'href="{REPO_URL}/{kind}/main/{resolved}{"#" + frag if frag else ""}"'
    return re.sub(r'href="([^"]+)"', fix, body)


def build_site(pages: list[tuple[str, str, str]], out_dir: Path, stamp: str) -> None:
    """pages : (fichier md source relatif au dépôt, nom html, libellé du menu)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".nojekyll").write_text("")
    site_pages = {src: name for src, name, _ in pages}
    for src, name, label in pages:
        md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"],
                               extension_configs={"toc": {"toc_depth": "2-2", "title": "Sommaire"}})
        text = (ROOT / src).read_text()
        body = md.convert(text)
        body = re.sub(r"<table>", '<div class="tw"><table>', body).replace("</table>", "</table></div>")
        if md.toc_tokens and len(md.toc) > 60 and "[TOC]" not in text:
            body = re.sub(r"(</h1>)", r"\1" + md.toc.replace('class="toc"', 'class="toc"'), body, count=1)
        body = rewrite_links(body, str(Path(src).parent), site_pages)
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), label)
        nav = "".join(f'<a href="{n}"{" class=on" if n == name else ""}>{html.escape(lab)}</a>' for _, n, lab in pages)
        (out_dir / name).write_text(PAGE.format(title=html.escape(title), css=CSS, nav=nav, body=body,
                                                repo=REPO_URL, stamp=stamp))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaign", action="append", required=True, help="ID de campagne (répétable, ordre = priorité croissante)")
    ap.add_argument("--site", default="docs", help="dossier du site statique (défaut : docs)")
    args = ap.parse_args()
    runs, metas = load(args.campaign)
    data = ROOT / "report" / "donnees.md"
    data.parent.mkdir(exist_ok=True)
    data.write_text(build_data_md(runs, metas))
    pages = [(p, h, l) for p, h, l in [("report/rapport-comite.md", "index.html", "Rapport"),
                                       ("report/donnees.md", "donnees.html", "Données par test"),
                                       ("02-PLAN-DE-TESTS.md", "plan.html", "Plan de tests"),
                                       ("01-ENVIRONNEMENT.md", "environnement.html", "Environnement")]
             if (ROOT / p).exists()]
    if pages and pages[0][1] != "index.html":
        pages[0] = (pages[0][0], "index.html", pages[0][2])
    stamp = max((m.get("finished_at") or m.get("started_at") or "")[:10] for m in metas)
    build_site(pages, Path(args.site) if Path(args.site).is_absolute() else ROOT / args.site, f"campagnes jusqu'au {stamp}")
    print(f"{data.relative_to(ROOT)} : {len(runs)} combinaisons test/variante/runtime ; site : {args.site}/ "
          f"({', '.join(h for _, h, _ in pages)})")


if __name__ == "__main__":
    main()
