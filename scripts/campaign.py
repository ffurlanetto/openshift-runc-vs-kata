"""Banc de comparaison runc vs Kata : precheck, exécution, rejeu. Seul prérequis cluster : kubectl.

Points d'entrée : ./precheck et ./run à la racine du dépôt (voir --help).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kvr.precheck import Precheck  # noqa: E402
from kvr.runner import (REPO_ROOT, Campaign, build_plan, discover_tests,  # noqa: E402
                        load_config, load_replay, log, replay_diffs, select_tests)
from kvr.target import build_target, choose_context, confirm, parse_selector  # noqa: E402


def csv(value: str | None) -> list[str] | None:
    return [v.strip().upper() if v.strip().isalpha() else v.strip()
            for v in value.split(",") if v.strip()] if value else None


def add_target_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("cible")
    g.add_argument("--context", help="contexte kube (sinon : choix interactif dans la liste)")
    g.add_argument("--env-id", help="identifiant d'environnement (ENV-A, ENV-B…) si pas de profil")
    g.add_argument("--kata-runtime-class", help="RuntimeClass Kata (sinon : profil ou détection)")
    g.add_argument("--node-selector", help="nœuds de bench, ex. kvr/bench=true")
    g.add_argument("--config", default=str(REPO_ROOT / "campaign.yaml"))


def add_selection_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("sélection")
    g.add_argument("--phases", help="phases à exécuter, ex. FUN,SEC (défaut : toutes)")
    g.add_argument("--skip", help="phases à exclure, ex. PERF,AGT")
    g.add_argument("--tests", help="IDs précis, ex. SEC-01,PERF-01")
    g.add_argument("--priority", help="P1, P2 ou P3")
    g.add_argument("--runtimes", default="runc,kata", help="défaut : runc,kata")


def resolve_phases(config: dict, phases: str | None, skip: str | None) -> list[str]:
    known = config["phases"]
    selected = csv(phases) or list(known)
    excluded = csv(skip) or []
    unknown = (set(selected) | set(excluded)) - set(known)
    if unknown:
        raise SystemExit(f"phases inconnues : {sorted(unknown)} (connues : {known})")
    return [p for p in known if p in selected and p not in excluded]


def apply_safe_mode(selected: list, explicit: list[str] | None, non_safe: bool) -> tuple[list, list[str]]:
    """Mode sûr (défaut) : les tests marqués `intrusive` dans leur META sont retirés du plan.
    Les demander explicitement (--tests) sans --non-safe est une erreur, pas un retrait silencieux."""
    if non_safe:
        return selected, []
    intrusive = [t for t in selected if t.meta.get("intrusive")]
    asked = [t.id for t in intrusive if explicit and t.id in explicit]
    if asked:
        raise SystemExit(f"tests intrusifs demandés en mode sûr : {', '.join(asked)}\n"
                         + "\n".join(f"  {t.id} : {t.meta['intrusive']}" for t in intrusive if t.id in asked)
                         + "\najouter --non-safe (accord écrit de l'exploitant et du SOC requis hors cluster jetable)")
    if intrusive:
        log("Mode sûr : tests intrusifs exclus (--non-safe pour les inclure) :")
        for t in intrusive:
            log(f"  - {t.id} : {t.meta['intrusive']}")
    return [t for t in selected if not t.meta.get("intrusive")], [t.id for t in intrusive]


def confirm_non_safe(tests: dict, plan: list[dict], yes: bool) -> None:
    ids = sorted({s["test_id"] for s in plan if tests[s["test_id"]].meta.get("intrusive")})
    if not ids:
        return
    log("\n⚠ MODE NON SÛR : tests intrusifs inclus. Ils reproduisent des techniques d'attaque et peuvent "
        "déclencher les outils de détection (SOC, EDR, Falco…) :")
    for i in ids:
        log(f"  - {i} : {tests[i].meta['intrusive']}")
    if yes:
        return
    if not sys.stdin.isatty():
        raise SystemExit("mode non interactif : --non-safe exige aussi --yes")
    answer = input("Accord de l'exploitant et du SOC obtenu ? Taper « intrusif » pour continuer : ").strip().lower()
    if answer != "intrusif":
        raise SystemExit("annulé")


def runtimes_of(value: str) -> list[str]:
    rts = [r.strip().lower() for r in value.split(",") if r.strip()]
    if set(rts) - {"runc", "kata"}:
        raise SystemExit("--runtimes : valeurs possibles runc, kata")
    return rts


def cmd_precheck(args) -> int:
    config = load_config(Path(args.config))
    ctx_entry = choose_context(args.context)
    cluster, target = build_target(config, ctx_entry, env_id=args.env_id or "precheck",
                                   kata_rc=args.kata_runtime_class,
                                   node_selector=parse_selector(args.node_selector))
    pc = Precheck(REPO_ROOT, config, cluster, target, resolve_phases(config, args.phases, args.skip),
                  runtimes_of(args.runtimes), smoke=not args.no_smoke)
    ok = pc.run()
    if args.output:
        Path(args.output).write_text(json.dumps(pc.report(), indent=2, ensure_ascii=False))
    print("\n" + ("Prérequis OK : ./run peut être lancé." if ok else "Prérequis NON satisfaits."))
    return 0 if ok else 1


def cmd_run(args) -> int:
    tests = discover_tests()
    old = load_replay(Path(args.replay)) if args.replay else None
    config = old["config"] if old else load_config(Path(args.config))
    if old:
        # Les profils ne sont pas enregistrés dans la campagne : on reprend ceux du dépôt.
        config["profiles"] = load_config(Path(args.config)).get("profiles", {})

    if args.print_images:
        from kvr.registry import registry_settings, resolve_charts, resolve_images
        settings = registry_settings(config, None)
        if args.context or sys.stdin.isatty():
            _, target = build_target(config, choose_context(args.context), env_id="print")
            settings = target["registry"]
        images, charts = resolve_images(config, settings), resolve_charts(config, settings)
        print("# Images à rendre disponibles (source → référence utilisée par le banc)")
        for k, src in config["images"].items():
            print(f"{k:<18} {src}\n{'':<18} → {images[k]}")
        print("\n# Charts Helm (préparation des composants)")
        for k, c in charts.items():
            print(f"{k:<18} {config['charts'][k]['ref']}:{c['version']}\n{'':<18} → {c['ref']}:{c['version']}")
        return 0

    if args.cleanup:
        ctx_entry = choose_context(args.context)
        cluster, _ = build_target(config, ctx_entry, env_id="cleanup")
        cluster.oc("delete", "ns", "-l", "kvr/managed=true", "--wait=false")
        log("Namespaces kvr supprimés (suppression asynchrone).")
        return 0

    # ---- plan
    if old:
        plan = old["plan"]
        phases = sorted({tests[s["test_id"]].meta["category"] for s in plan if s["test_id"] in tests})
        unknown = {s["test_id"] for s in plan} - set(tests)
        if unknown:
            raise SystemExit(f"tests du plan absents du dépôt : {sorted(unknown)}")
        runtimes = sorted({s["runtime"] for s in plan})
        if not args.non_safe:
            excluded = sorted({s["test_id"] for s in plan if tests[s["test_id"]].meta.get("intrusive")})
            plan = [s for s in plan if s["test_id"] not in excluded]
            if excluded:
                log(f"⚠ rejeu en mode sûr : tests intrusifs retirés du plan ({', '.join(excluded)}) ; "
                    "--non-safe pour un rejeu identique")
        else:
            excluded = []
    else:
        phases = resolve_phases(config, args.phases, args.skip)
        runtimes = runtimes_of(args.runtimes)
        selected = [t for t in select_tests(tests, csv(args.tests), None, args.priority)
                    if t.meta["category"] in phases]
        selected, excluded = apply_safe_mode(selected, csv(args.tests), args.non_safe)
        if not selected:
            raise SystemExit(f"aucun test automatisé pour phases={phases} tests={args.tests} "
                             f"priorité={args.priority} (voir ./run --list)")
        plan = build_plan(selected, config, runtimes, args.runs, not args.no_warmup)

    if args.dry_run:
        for s in plan:
            print(f"{s['test_id']:<8} {s['runtime']:<5} run {s['run']}"
                  f"{' ' + s['variant'] if s.get('variant') else ''}{' (warm-up)' if s['run'] == 0 else ''}")
        print(f"\n{len(plan)} exécutions, phases {phases}, runtimes {runtimes}")
        return 0

    # ---- cible
    ctx_entry = choose_context(args.context)
    cluster, target = build_target(config, ctx_entry, env_id=args.env_id, kata_rc=args.kata_runtime_class,
                                   node_selector=parse_selector(args.node_selector),
                                   previous=old["target"] if old else None)
    confirm(target, cluster.platform_version(), args.yes)
    if args.non_safe:
        confirm_non_safe(tests, plan, args.yes)

    replay_of = None
    if old:
        diffs = replay_diffs(old, cluster, target)
        log(f"\nRejeu de {old['campaign_id']} ({len(plan)} exécutions)")
        for d in diffs or ["aucun écart : code et environnement identiques"]:
            log(f"  - {d}")
        if diffs and args.strict:
            raise SystemExit("--strict : rejeu refusé tant que des écarts existent")
        replay_of = {"campaign_id": old["campaign_id"], "diff": diffs}
        if old.get("allow_destructive") and not args.allow_destructive:
            log("⚠ campagne d'origine lancée avec --allow-destructive : ajouter l'option pour un rejeu identique")

    # ---- precheck (toujours)
    pc = Precheck(REPO_ROOT, config, cluster, target, phases, runtimes, smoke=not args.no_smoke)
    if not pc.run():
        raise SystemExit("\nPrécheck en échec : campagne non lancée.")

    campaign = Campaign(config, cluster, target, plan, tests, args.allow_dirty, replay_of, pc.report(),
                        allow_destructive=args.allow_destructive, safe_mode=not args.non_safe,
                        excluded_intrusive=excluded)
    return campaign.execute()


def cmd_list(_args) -> int:
    for t in discover_tests().values():
        m = t.meta
        print(f"{t.id:<8} {m.get('priority', '-'):<3} {m['category']:<5} {m['title']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("precheck", help="contrôle les prérequis (outils, accès, droits, cluster, smoke test)")
    add_target_args(p)
    add_selection_args(p)
    p.add_argument("--no-smoke", action="store_true", help="ne pas lancer de pod de test")
    p.add_argument("--output", help="écrit le rapport de precheck en JSON")
    p.set_defaults(func=cmd_precheck)

    p = sub.add_parser("run", help="lance la campagne (precheck inclus)")
    add_target_args(p)
    add_selection_args(p)
    g = p.add_argument_group("exécution")
    g.add_argument("--runs", type=int, help="surcharge le nombre de runs mesurés")
    g.add_argument("--no-warmup", action="store_true")
    g.add_argument("--no-smoke", action="store_true", help="precheck sans pod de test")
    g.add_argument("--dry-run", action="store_true", help="affiche le plan sans rien exécuter")
    g.add_argument("--yes", "-y", action="store_true", help="pas de confirmation (CI, non interactif)")
    g.add_argument("--allow-dirty", action="store_true", help="autorise un arbre git modifié")
    g.add_argument("--non-safe", action="store_true",
                   help="inclut les tests intrusifs (pods privilégiés lisant le nœud, abus de ressources) : "
                        "exclus par défaut ; accord de l'exploitant et du SOC requis hors cluster jetable")
    g.add_argument("--allow-destructive", action="store_true",
                   help="exécute réellement les scénarios pouvant rendre un nœud indisponible "
                        "(ex. FUN-30 en Kata) : clusters jetables uniquement")
    g = p.add_argument_group("rejeu et maintenance")
    g.add_argument("--replay", metavar="CAMPAIGN_JSON", help="rejoue à l'identique une campagne enregistrée")
    g.add_argument("--strict", action="store_true", help="avec --replay : refuse si code/environnement diffèrent")
    g.add_argument("--cleanup", action="store_true", help="supprime les namespaces kvr restants et quitte")
    g.add_argument("--print-images", action="store_true",
                   help="liste les images et charts (après réécriture miroir) à mirrorer, et quitte")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("list", help="liste les tests automatisés")
    p.set_defaults(func=cmd_list)

    args = ap.parse_args()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ninterrompu : ./run --cleanup pour supprimer les namespaces restants")
        return 130


if __name__ == "__main__":
    sys.exit(main())
