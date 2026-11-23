"""DIND-01 : démarrage du moteur de build dans le pod de CI (V1 à V4).

Mesure le délai pod Ready + moteur opérationnel, et relève pilote de stockage, version de cgroups,
version du moteur. En Kata, le stockage du moteur est un emptyDir vu à travers virtio-fs.
"""

from kvr import dind

META = {"id": "DIND-01", "category": "DIND", "aspect": "FUN", "priority": "P1",
        "title": "Démarrage du moteur de build", "variants": dind.VARIANTS, "runs": 3}


def run(ctx):
    pod_ready = dind.deploy(ctx)
    engine_ready = dind.wait_engine(ctx)
    facts = dind.info(ctx)
    ctx.evidence("engine-info.json", facts)
    ctx.metric("pod_ready", round(pod_ready, 1), "s", "lower")
    ctx.metric("engine_ready_after_pod", round(engine_ready, 1), "s", "lower")
    ctx.metric("engine_ready_total", round(pod_ready + engine_ready, 1), "s", "lower")
    ctx.observe(f"{ctx.variant} : moteur prêt en {pod_ready + engine_ready:.1f}s ; " +
                ", ".join(f"{k}={v}" for k, v in facts.items() if v))
    return "PASS"
