"""SCR-02 : rotation d'un secret natif, délai de propagation jusqu'au conteneur.

Trois secrets, consommés par un même pod :
- `few`  : 3 clés (cas courant) ;
- `many` : `many_keys` clés (au-delà de la limite de copie de l'agent Kata, à vérifier selon la version) ;
- `env`  : consommé en variable d'environnement et en `subPath` (jamais mis à jour, dans les deux runtimes).
On remplace une clé de chaque secret, puis on interroge le conteneur toutes les `poll_s` secondes
jusqu'à voir la nouvelle valeur (ou `timeout_s`).
"""

import time

from kvr import secrets

META = {"id": "SCR-02", "category": "SCR", "aspect": "FUN", "priority": "P1",
        "title": "Secret natif : propagation d'une rotation", "runs": 3,
        "params": {"many_keys": 40, "timeout_s": 240, "poll_s": 2}}


def _data(n: int, version: str) -> dict[str, bytes]:
    return {f"k{i:02d}": f"kvr-{version}-{i}".encode() for i in range(n)}


def run(ctx):
    n_many = int(ctx.params["many_keys"])
    secrets.create_secret(ctx, "few", _data(3, "v1"))
    secrets.create_secret(ctx, "many", _data(n_many, "v1"))
    secrets.create_secret(ctx, "env", _data(1, "v1"))
    ctx.apply_template("secret-pod.yaml.j2", name="consumer",
                       secret_volumes=[{"name": "few", "secret": "few"}, {"name": "many", "secret": "many"}],
                       subpaths=[{"secret": "env", "key": "k00", "path": "/etc/kvr-k00"}],
                       env_secrets=[{"var": "KVR_K00", "secret": "env", "key": "k00"}])
    ctx.wait("pod/consumer", timeout_s=240)

    targets = {"few": "/secrets/few/k00", "many": f"/secrets/many/k{n_many - 1:02d}", "subpath": "/etc/kvr-k00"}
    new = {"few": secrets.sha(b"kvr-v2-0"), "many": secrets.sha(f"kvr-v2-{n_many - 1}".encode()),
           "subpath": secrets.sha(b"kvr-v2-0")}
    before = secrets.file_digests(ctx, "consumer", list(targets.values()))
    assert before[targets["few"]] == secrets.sha(b"kvr-v1-0"), "valeur initiale incorrecte"

    t0 = time.perf_counter()
    secrets.create_secret(ctx, "few", _data(3, "v2"), verb="replace")
    secrets.create_secret(ctx, "many", _data(n_many, "v2"), verb="replace")
    secrets.create_secret(ctx, "env", _data(1, "v2"), verb="replace")
    delays: dict[str, float | None] = {k: None for k in targets}
    timeout, poll = float(ctx.params["timeout_s"]), float(ctx.params["poll_s"])
    timeline = []
    while time.perf_counter() - t0 < timeout and any(delays[k] is None for k in ("few", "many")):
        seen = secrets.file_digests(ctx, "consumer", list(targets.values()))
        el = round(time.perf_counter() - t0, 1)
        timeline.append({"t": el, **{k: seen[p] == new[k] for k, p in targets.items()}})
        for k, p in targets.items():
            if delays[k] is None and seen[p] == new[k]:
                delays[k] = el
        time.sleep(poll)
    _, env_now, _ = ctx.exec("consumer", ["sh", "-c", 'printf "%s" "$KVR_K00" | sha256sum | cut -c1-64'])
    ctx.evidence("timeline.json", timeline)

    for k in ("few", "many"):
        if delays[k] is not None:
            ctx.metric(f"propagation_{k}", delays[k], "s", "lower")
    ctx.metric("subpath_updated", int(delays["subpath"] is not None), "bool", "lower")
    env_updated = env_now.strip() == secrets.sha(b"kvr-v2-0")
    ctx.metric("env_updated", int(env_updated), "bool", "lower")
    fmt = lambda d: f"{d} s" if d is not None else f"NON propagé après {timeout:.0f} s"  # noqa: E731
    ctx.observe(f"{ctx.runtime} : rotation propagée en {fmt(delays['few'])} (3 clés), "
                f"{fmt(delays['many'])} ({n_many} clés) ; subPath "
                f"{'mis à jour (inattendu)' if delays['subpath'] is not None else 'non mis à jour (attendu)'} ; "
                f"variable d'environnement {'mise à jour (inattendu)' if env_updated else 'inchangée (attendu)'}")
    if delays["few"] is None:
        return "FAIL"
    if delays["many"] is None:
        return "PARTIAL"
    return "PASS"
