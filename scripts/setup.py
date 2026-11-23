"""Préparation des composants du banc sur un cluster de TEST (jamais sur un cluster partagé sans accord).

  ./setup kyverno [--context X]     installe Kyverno (chart épinglé dans campaign.yaml, miroir appliqué)
  ./setup kata    [--context X]     installe Kata Containers upstream via kata-deploy (pas OSC)

Ne touche pas un composant installé hors du banc : sur les clusters distants, l'existant est utilisé tel quel.
Une installation faite par ./setup peut être mise à jour en relançant la commande.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kvr import kyverno  # noqa: E402
from kvr.registry import resolve_charts, resolve_images  # noqa: E402
from kvr.runner import REPO_ROOT, load_config  # noqa: E402
from kvr.target import build_target, choose_context, confirm  # noqa: E402


def drop_failed_release(release: str, ns: str, context: str) -> None:
    """Une release jamais déployée (installation en échec, désinstallation interrompue…) bloque
    `helm upgrade --install` : on la retire, sans hooks (ils dépendent d'objets jamais créés)."""
    base = ["-n", ns, "--kube-context", context]
    r = subprocess.run(["helm", "history", release, *base, "-o", "json"], capture_output=True, text=True)
    if r.returncode != 0:
        return  # release inexistante
    history = json.loads(r.stdout or "[]")
    if any(h.get("status") in ("deployed", "superseded") for h in history):
        return
    print(f"Release {release} jamais déployée ({history[-1].get('status')}) : retrait avant nouvel essai")
    subprocess.run(["helm", "uninstall", release, *base, "--no-hooks"], check=False)


def grant_scc(cluster, ns: str, scc: str) -> None:
    """Autorise une SCC pour tous les ServiceAccounts du namespace (RoleBinding, kubectl seul)."""
    name = f"kvr-scc-{scc}"
    if cluster.oc("get", "rolebinding", name, "-n", ns, check=False).returncode != 0:
        cluster.oc("create", "rolebinding", name, "-n", ns,
                   f"--clusterrole=system:openshift:scc:{scc}", f"--group=system:serviceaccounts:{ns}")


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
    ns = "kyverno"
    drop_failed_release("kyverno", ns, ctx_entry["name"])
    if cluster.oc("get", "ns", ns, check=False).returncode != 0:
        cluster.oc("create", "ns", ns)
    if cluster.is_openshift:
        # Le chart fixe runAsUser 65534 : refusé par restricted-v2 (plage d'UID du namespace).
        # nonroot-v2 accepte tout UID non nul, sans autre privilège.
        grant_scc(cluster, ns, "nonroot-v2")
    cmd = ["helm", "upgrade", "--install", "kyverno", chart["ref"], "--version", str(chart["version"]),
           "--kube-context", ctx_entry["name"], "--namespace", ns,
           "--wait", "--timeout", "10m"]
    print("→ " + " ".join(cmd))
    rc = subprocess.run(cmd).returncode
    if rc == 0:
        print(f"Kyverno installé : {kyverno.detect(cluster)}")
    return rc


# Labels des paquets OSC / container-selinux appliqués aux chemins de kata-deploy (/opt -> /var/opt sur RHCOS).
SELINUX_FCONTEXTS = [
    ("qemu_exec_t", "/var/opt/kata/bin/qemu-system-.*"),
    ("bin_t", "/var/opt/kata/libexec(/.*)?"),
    ("usr_t", "/var/opt/kata/share(/.*)?"),
]


def relabel_nodes(cluster, ns: str, image: str, selector: dict, apply: bool = True) -> bool:
    """Sur RHCOS (SELinux enforcing), le shim lance QEMU et virtiofsd en container_kvm_t : leurs binaires
    doivent porter un type autorisé comme point d'entrée. Persistant (semanage), idempotent.
    apply=False retire ces labels (retour à var_t) : l'installeur kata-deploy ne peut réécrire que du var_t,
    donc toute mise à jour se fait labels retirés, puis labels réappliqués."""
    if apply:
        steps = [f'(semanage fcontext -a -t {t} "{p}" 2>/dev/null || semanage fcontext -m -t {t} "{p}")'
                 for t, p in SELINUX_FCONTEXTS]
    else:
        steps = [f'(semanage fcontext -d "{p}" 2>/dev/null || true)' for _, p in SELINUX_FCONTEXTS]
    script = " && ".join(steps + ["(restorecon -R /var/opt/kata 2>/dev/null || true)",
                                  "ls -Z /var/opt/kata/bin/qemu-system-* /var/opt/kata/libexec/virtiofsd 2>/dev/null || true"])
    ok = True
    for node in cluster.nodes(selector or {"katacontainers.io/kata-runtime": "true"}):
        name = node["metadata"]["name"]
        r = cluster.oc("debug", f"node/{name}", "-n", ns, "--profile=sysadmin", f"--image={image}", "--quiet",
                       "--", "chroot", "/host", "sh", "-c", script, check=False, timeout=300)
        print(f"  {'pose' if apply else 'retrait'} des labels SELinux {name} : {'OK' if r.returncode == 0 else 'ÉCHEC'}")
        for line in [x for x in (r.stdout + r.stderr).strip().splitlines() if not x.startswith("Warning:")][-3:]:
            print(f"    {line}")
        ok &= r.returncode == 0
    # Les pods de debug terminés (node-debugger-*) restent dans le namespace : ménage.
    for p in cluster.get_json("get", "pods", "-n", ns)["items"]:
        if p["metadata"]["name"].startswith("node-debugger-") and p["status"].get("phase") in ("Succeeded", "Failed"):
            cluster.oc("delete", "pod", p["metadata"]["name"], "-n", ns, "--wait=false", check=False)
    return ok


def setup_kata(config: dict, args) -> int:
    """kata-deploy upstream. Sur OpenShift x86_64, préférer l'operator OSC (support Red Hat)."""
    ctx_entry = choose_context(args.context)
    cluster, target = build_target(config, ctx_entry, env_id="setup")
    if not shutil.which("helm"):
        raise SystemExit("helm introuvable (requis pour ./setup)")
    ns = "kata-deploy"
    ours = subprocess.run(["helm", "status", "kata-deploy", "-n", ns, "--kube-context", ctx_entry["name"]],
                          capture_output=True).returncode == 0
    existing = [rc["metadata"]["name"] for rc in cluster.runtime_classes() if "kata" in rc.get("handler", "")]
    if existing and not ours:
        print(f"RuntimeClass Kata déjà présentes ({existing}), installées hors du banc : rien à faire.")
        return 0
    chart = resolve_charts(config, target["registry"])["kata-deploy"]
    profile = (config.get("profiles") or {}).get(target["api_server"]) or {}
    values = [chart["values"], *profile.get("kata_deploy_values", [])]
    confirm(target, cluster.platform_version(), args.yes)
    print("⚠ kata-deploy modifie les nœuds (binaires dans /opt/kata, configuration CRI-O, module SELinux)"
          " et redémarre CRI-O : réservé aux clusters de test.")
    print(f"  {'mise à jour' if ours else 'installation'} ; valeurs : {', '.join(values)}")
    if cluster.oc("get", "ns", ns, check=False).returncode != 0:
        cluster.oc("create", "ns", ns)
    cluster.oc("label", "ns", ns, "--overwrite", "pod-security.kubernetes.io/enforce=privileged",
               *(["security.openshift.io/scc.podSecurityLabelSync=false"] if cluster.is_openshift else []))
    if cluster.is_openshift:
        # Les pods d'installation sont privilégiés et montent l'hôte : SCC privileged pour les SA du namespace.
        grant_scc(cluster, ns, "privileged")
    image = resolve_images(config, target["registry"])["ubi_minimal"]
    selector = target.get("node_selector") or {}
    if cluster.is_openshift and ours:
        print("Retrait des labels SELinux posés par le banc (l'installeur doit pouvoir réécrire /opt/kata) :")
        if not relabel_nodes(cluster, ns, image, selector, apply=False):
            return 1
    cmd = ["helm", "upgrade", "--install", "kata-deploy", chart["ref"], "--version", str(chart["version"]),
           "--kube-context", ctx_entry["name"], "--namespace", ns,
           *[a for v in values for a in ("-f", str(REPO_ROOT / v))], "--wait", "--timeout", "30m"]
    print("→ " + " ".join(cmd))
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        return rc
    if cluster.is_openshift:
        print("Labels SELinux des binaires Kata (comme les paquets OSC) :")
        if not relabel_nodes(cluster, ns, image, selector, apply=True):
            return 1
    names = [r["metadata"]["name"] + "→" + r["handler"] for r in cluster.runtime_classes()]
    print(f"RuntimeClass : {names}")
    print("Vérifier ensuite : ./precheck (smoke test d'un vrai pod Kata)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("component", choices=["kyverno", "kata"])
    ap.add_argument("--context")
    ap.add_argument("--yes", "-y", action="store_true")
    ap.add_argument("--config", default=str(REPO_ROOT / "campaign.yaml"))
    args = ap.parse_args()
    config = load_config(Path(args.config))
    return {"kyverno": setup_kyverno, "kata": setup_kata}[args.component](config, args)


if __name__ == "__main__":
    sys.exit(main())
