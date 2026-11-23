"""Choix du contexte kube et construction de la cible (cluster + réglages de campagne)."""

from __future__ import annotations

import sys

from .cluster import Cluster, OcError, list_contexts
from .registry import registry_settings


def interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{prompt}{suffix} : ").strip()
    except EOFError:
        raise SystemExit("\nentrée interrompue") from None
    return answer or (default or "")


def choose_context(requested: str | None) -> dict:
    """Retourne le contexte demandé, ou le fait choisir dans la liste du kubeconfig."""
    contexts = list_contexts()
    if not contexts:
        raise SystemExit("aucun contexte dans le kubeconfig (KUBECONFIG ou ~/.kube/config)")
    if requested:
        for c in contexts:
            if c["name"] == requested:
                return c
        raise SystemExit(f"contexte inconnu : {requested}")
    if not interactive():
        raise SystemExit("mode non interactif : préciser --context <nom>")
    print("Contextes kube disponibles :")
    default_idx = 1
    for i, c in enumerate(contexts, 1):
        mark = "*" if c["current"] else " "
        if c["current"]:
            default_idx = i
        print(f"  {i:>2}) {mark} {c['name']:<45} {c['server']}")
    while True:
        choice = ask("Numéro du contexte à utiliser", str(default_idx))
        if choice.isdigit() and 1 <= int(choice) <= len(contexts):
            return contexts[int(choice) - 1]
        print("  choix invalide")


def parse_selector(value: str | None) -> dict | None:
    if value is None:
        return None
    sel = {}
    for part in filter(None, (p.strip() for p in value.split(","))):
        k, _, v = part.partition("=")
        sel[k] = v
    return sel


def detect_kata_runtime_class(cluster: Cluster) -> tuple[str | None, list[str]]:
    """RuntimeClass Kata candidates (nom ou handler contenant 'kata')."""
    try:
        rcs = cluster.runtime_classes()
    except OcError:
        return None, []
    names = sorted(rc["metadata"]["name"] for rc in rcs
                   if "kata" in rc["metadata"]["name"] or "kata" in rc.get("handler", ""))
    return (names[0] if len(names) == 1 else None), names


def build_target(config: dict, ctx_entry: dict, *, env_id: str | None = None,
                 kata_rc: str | None = None, node_selector: dict | None = None,
                 previous: dict | None = None) -> tuple[Cluster, dict]:
    """Assemble la cible : flags > profil (par API server) > campagne d'origine (replay) > détection."""
    cluster = Cluster(ctx_entry["name"])
    server = cluster.api_server()
    profile = (config.get("profiles") or {}).get(server, {})
    prev = previous if previous and previous.get("api_server") == server else {}

    if not kata_rc:
        kata_rc = profile.get("kata_runtime_class") or (previous or {}).get("runtimes", {}).get("kata")
    if not kata_rc:
        detected, candidates = detect_kata_runtime_class(cluster)
        if detected:
            kata_rc = detected
        elif len(candidates) > 1:
            if not interactive():
                raise SystemExit(f"plusieurs RuntimeClass Kata ({candidates}) : préciser --kata-runtime-class")
            kata_rc = ask(f"RuntimeClass Kata à utiliser {candidates}", candidates[0])
        else:
            kata_rc = "kata"  # absente : les exécutions kata seront BLOCKED (signalé par le precheck)

    env_id = env_id or profile.get("env_id") or prev.get("env_id")
    if not env_id:
        if not interactive():
            raise SystemExit("identifiant d'environnement inconnu pour ce cluster : préciser --env-id (ex. ENV-B)")
        env_id = ask("Identifiant d'environnement (voir 02-PLAN-DE-TESTS §3)", "ENV-X")

    target = {
        "context": ctx_entry["name"],
        "api_server": server,
        "platform": cluster.platform,
        "env_id": env_id,
        "description": profile.get("description") or prev.get("description", ""),
        "nested_virt": bool(profile.get("nested_virt", prev.get("nested_virt", False))),
        "kata_version": profile.get("kata_version") or prev.get("kata_version", ""),
        "node_selector": (node_selector if node_selector is not None
                          else profile.get("node_selector", prev.get("node_selector", {}))),
        "runtimes": {"runc": None, "kata": kata_rc},
        "registry": registry_settings(config, profile),
    }
    return cluster, target


def confirm(target: dict, version: str, yes: bool) -> None:
    print("\nCible :")
    for k in ("context", "api_server", "platform", "env_id", "description", "node_selector"):
        print(f"  {k:<14} {target[k]}")
    reg = target["registry"]
    print(f"  {'miroirs':<14} {[m['from'] + ' → ' + m['to'] for m in reg['mirrors']] or 'aucun (pull direct ou miroir géré par le cluster)'}")
    print(f"  {'pull secret':<14} {(reg['pull_secret'] or {}).get('name', 'aucun')}")
    print(f"  {'version':<14} {version}")
    print(f"  {'kata':<14} RuntimeClass '{target['runtimes']['kata']}'")
    if yes:
        return
    if not interactive():
        raise SystemExit("mode non interactif : ajouter --yes pour confirmer la cible")
    print("\n⚠ La campagne crée des namespaces, des pods privilégiés et exécute des tests d'évasion.")
    if ask("Confirmer l'exécution sur ce cluster ? (oui/non)", "non").lower() not in ("o", "oui", "y", "yes"):
        raise SystemExit("annulé")
