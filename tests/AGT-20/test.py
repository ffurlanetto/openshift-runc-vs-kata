"""AGT-20 : arrêt d'urgence d'une sandbox d'agent.

Le processus de l'agent ignore SIGTERM (PID 1 sans gestionnaire). Délai de grâce `grace` secondes.
Mesure le délai entre `kubectl delete pod` et la disparition effective du pod (kubelet a confirmé
l'arrêt de tous les processus ; en Kata, arrêt de la VM).
"""

import time

META = {"id": "AGT-20", "category": "AGT", "aspect": "SEC", "priority": "P1", "agent_mode": "replay",
        "title": "Arrêt d'urgence (processus ignorant SIGTERM)", "runs": 3, "params": {"grace": 5}}


def run(ctx):
    grace = int(ctx.params["grace"])
    ctx.apply_template("probe-pod.yaml.j2", grace=grace)
    ctx.wait("pod/probe")
    t0 = time.perf_counter()
    ctx.oc("delete", "pod", "probe", "-n", ctx.namespace, "--wait=false")
    gone = None
    while time.perf_counter() - t0 < grace + 180:
        r = ctx.oc("get", "pod", "probe", "-n", ctx.namespace, "-o", "name", check=False)
        if r.returncode != 0 and "NotFound" in r.stderr:
            gone = time.perf_counter() - t0
            break
        time.sleep(0.5)
    if gone is None:
        ctx.observe(f"pod toujours présent {grace + 180}s après la suppression")
        return "FAIL"
    ctx.metric("time_to_gone", round(gone, 1), "s", "lower")
    ctx.metric("beyond_grace", round(gone - grace, 1), "s", "lower")
    ctx.observe(f"{ctx.runtime} : pod supprimé en {gone:.1f}s (grâce {grace}s, dépassement {gone - grace:.1f}s)")
    return "PASS"
