"""SCR-01 : secret natif consommé de toutes les manières usuelles, contenu identique octet par octet.

Un secret « fichiers » (petit texte, binaire, gros ~700 KiB) et un secret immuable sont consommés par :
volume complet, volume avec `items` + mode, volume projeté (secret + downward API), `subPath`,
variable d'environnement, et un volume `optional` sur un secret absent (le pod doit démarrer).
On compare les sha256 vus dans le conteneur aux sha256 envoyés.
"""

from kvr import secrets

META = {"id": "SCR-01", "category": "SCR", "aspect": "FUN", "priority": "P1",
        "title": "Secret natif : tous les modes de consommation", "runs": 3,
        "params": {"large_kib": 700}}


def run(ctx):
    large = int(ctx.params["large_kib"]) * 1024
    data = {"small": b"kvr-valeur-factice",
            "binary": secrets.fake_bytes("kvr-binary", 4096),
            "large": secrets.fake_bytes("kvr-large", large)}
    exp = secrets.create_secret(ctx, "files", data)
    exp_imm = secrets.create_secret(ctx, "frozen", {"token": b"kvr-immuable"}, immutable=True)

    ctx.apply_template("secret-pod.yaml.j2", name="consumer",
                       secret_volumes=[{"name": "full", "secret": "files"},
                                       {"name": "items", "secret": "files", "default_mode": 288,  # 0440
                                        "items": [{"key": "binary", "path": "nested/bin.dat"}]},
                                       {"name": "frozen", "secret": "frozen"},
                                       {"name": "missing", "secret": "does-not-exist", "optional": True}],
                       projected=True, projected_secret="files",
                       subpaths=[{"secret": "files", "key": "small", "path": "/etc/kvr-small"}],
                       env_secrets=[{"var": "KVR_SMALL", "secret": "files", "key": "small"}])
    ready = ctx.wait("pod/consumer", timeout_s=240)
    ctx.metric("pod_ready", round(ready, 2), "s", "lower")

    checks = {"/secrets/full/small": exp["small"], "/secrets/full/binary": exp["binary"],
              "/secrets/full/large": exp["large"], "/secrets/items/nested/bin.dat": exp["binary"],
              "/secrets/frozen/token": exp_imm["token"], "/secrets/projected/secret-small": exp["small"],
              "/etc/kvr-small": exp["small"]}
    seen = secrets.file_digests(ctx, "consumer", list(checks))
    _, env_out, _ = ctx.exec("consumer", ["sh", "-c", 'printf "%s" "$KVR_SMALL" | sha256sum | cut -c1-64'])
    seen["env:KVR_SMALL"] = env_out.strip()
    checks["env:KVR_SMALL"] = exp["small"]
    _, meta, _ = ctx.exec("consumer", ["sh", "-c",
                                       "cat /secrets/projected/pod-name; echo; ls -A /secrets/missing | wc -l; "
                                       "stat -L -c '%a %u %g' /secrets/items/nested/bin.dat; "
                                       "stat -c '%a' /secrets/full/small 2>/dev/null; "
                                       "awk '$2 ~ /^\\/secrets\\// {print $2, $3}' /proc/mounts"])
    lines = meta.splitlines()
    ctx.evidence("seen.json", {"expected": checks, "seen": seen, "details": lines})

    bad = [p for p, d in checks.items() if seen.get(p) != d]
    downward_ok = bool(lines) and lines[0].strip() == "consumer"
    fstypes = sorted({l.split()[1] for l in lines[4:] if len(l.split()) == 2})
    ctx.metric("mismatched_paths", len(bad), "count", "lower")
    ctx.observe(f"{ctx.runtime} : {len(checks) - len(bad)}/{len(checks)} contenus identiques"
                f"{' (écarts : ' + ', '.join(bad) + ')' if bad else ''} ; downward API "
                f"{'OK' if downward_ok else 'KO'} ; volume optional absent : pod démarré ; "
                f"mode items {lines[2] if len(lines) > 2 else '?'} ; types de montage {fstypes}")
    return "PASS" if not bad and downward_ok else "FAIL"
