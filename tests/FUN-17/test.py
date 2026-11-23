"""FUN-17 : dépassement de limits.memory.

Attendu (runc et kata) : le conteneur est tué avec la raison `OOMKilled`, remontée
correctement par Kubernetes. PARTIAL si le conteneur meurt en 137 sans la bonne raison.
"""

import time

META = {
    "id": "FUN-17",
    "category": "FUN",
    "aspect": "FUN",
    "priority": "P1",
    "title": "OOM : dépassement de limits.memory",
    "params": {"memory_limit": "128Mi"},
}


def run(ctx):
    t0 = time.perf_counter()
    ctx.apply_template("oom-pod.yaml.j2")
    cs = ctx.wait_terminated("oom", timeout_s=240)
    ctx.metric("time_to_oom", round((time.perf_counter() - t0) * 1000), "ms", "lower")

    term = cs["state"].get("terminated") or cs["lastState"].get("terminated")
    reason, code = term.get("reason"), term.get("exitCode")
    ctx.observe(f"limite {ctx.params['memory_limit']} ; terminated reason={reason} exitCode={code}")
    if reason == "OOMKilled":
        return "PASS"
    if code == 137:
        return "PARTIAL"
    return "FAIL"
