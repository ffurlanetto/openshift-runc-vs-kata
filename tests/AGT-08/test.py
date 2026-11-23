"""AGT-08 : latence d'un appel d'outil de l'agent (exec).

Un agent exécute des centaines de commandes courtes. Chemin mesuré : client → API server → kubelet
→ CRI → (agent Kata dans la VM) → processus. n commandes `true` consécutives, harnais rejoué.
"""

import statistics
import time

META = {"id": "AGT-08", "category": "AGT", "aspect": "PERF", "priority": "P1", "agent_mode": "replay",
        "title": "Latence d'un appel d'outil (exec)", "runs": 3, "params": {"n": 100}}


def run(ctx):
    ctx.apply_template("probe-pod.yaml.j2")
    ctx.wait("pod/probe")
    lat, failures = [], 0
    for _ in range(int(ctx.params["n"])):
        t0 = time.perf_counter()
        rc, _, _ = ctx.exec("probe", ["true"])
        lat.append((time.perf_counter() - t0) * 1000)
        failures += rc != 0
    lat.sort()
    p50 = statistics.median(lat)
    p95 = lat[int(0.95 * (len(lat) - 1))]
    ctx.metric("exec_latency_p50", round(p50), "ms", "lower")
    ctx.metric("exec_latency_p95", round(p95), "ms", "lower")
    ctx.metric("exec_failures", failures, "count", "lower")
    ctx.evidence("latencies_ms.json", [round(x, 1) for x in lat])
    ctx.observe(f"{len(lat)} exec : p50 {p50:.0f} ms, p95 {p95:.0f} ms, échecs {failures}")
    return "PASS" if failures == 0 else "FAIL"
