"""PERF-01 : latence de démarrage d'un pod (création → Ready).

Mesure côté client : de l'envoi du manifeste au retour de `oc wait` (watch).
Le coût de lancement du binaire oc est identique pour runc et kata et s'annule dans le Δ.
Mesure côté serveur en complément (résolution 1 s) : creationTimestamp → condition Ready.
Le run 0 (warm-up) pré-tire l'image : les runs mesurés n'incluent pas le pull.
"""

import datetime as dt
import time

META = {
    "id": "PERF-01",
    "category": "PERF",
    "aspect": "PERF",
    "priority": "P1",
    "title": "Latence de démarrage d'un pod",
    "runs": 30,
}


def _ts(s: str) -> dt.datetime:
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def run(ctx):
    t0 = time.perf_counter()
    ctx.apply_template("probe-pod.yaml.j2")
    ctx.wait("pod/probe", timeout_s=300)
    latency_ms = round((time.perf_counter() - t0) * 1000)
    ctx.metric("pod_ready_latency", latency_ms, "ms", "lower")

    pod = ctx.get("pod/probe")
    ready = next(c for c in pod["status"]["conditions"] if c["type"] == "Ready")
    server_s = (_ts(ready["lastTransitionTime"]) - _ts(pod["metadata"]["creationTimestamp"])).total_seconds()
    ctx.metric("pod_ready_latency_server", server_s, "s", "lower")
    return "PASS"
