"""DIND-06 : conteneurs lancés par le pipeline (tests d'intégration, docker compose).

V1/V2 : un conteneur lancé par le dind interne joint une URL HTTPS (TLS = paquets pleins, révèle
un trou de MTU). Relevé des MTU : interface du pod (OVN-K) vs bridge Docker interne.
URL surchargeable (site airgappé) : campaign.yaml › overrides.DIND-06.params.url
"""

from kvr import dind

META = {"id": "DIND-06", "category": "DIND", "aspect": "FUN", "priority": "P1",
        "title": "Conteneurs imbriqués : réseau et MTU", "variants": dind.DOCKER_VARIANTS, "runs": 3,
        "params": {"url": "https://registry.access.redhat.com/v2/"}}


def run(ctx):
    dind.deploy(ctx)
    dind.wait_engine(ctx)
    _, pod_mtu, _ = dind.sh(ctx, "cat /sys/class/net/eth0/mtu")
    _, bridge_mtu, _ = dind.sh(ctx, "docker network inspect bridge --format "
                                    "'{{index .Options \"com.docker.network.driver.mtu\"}}' 2>/dev/null")
    base = ctx.images["ubi_minimal"]
    url = ctx.params["url"]
    rc, out, err = dind.sh(ctx, f"docker run --rm {base} curl -sS -o /dev/null --max-time 60 "
                                f"-w '%{{http_code}} %{{time_total}}' {url} 2>&1", timeout_s=300)
    ctx.evidence("nested-curl.txt", f"rc={rc}\n{out}{err}")
    last = (out.strip().splitlines() or [""])[-1]
    parts = last.split()
    code = parts[0] if parts else "000"
    reachable = code not in ("", "000")
    ctx.metric("nested_https_ok", int(reachable), "bool", "higher")
    if reachable and len(parts) > 1:
        ctx.metric("nested_https_time", round(float(parts[1]) * 1000), "ms", "lower")
    ctx.observe(f"{ctx.variant} : MTU pod={pod_mtu.strip()} bridge docker={bridge_mtu.strip() or '1500 (défaut)'} ; "
                f"HTTPS depuis un conteneur imbriqué : {'OK' if reachable else 'ÉCHEC'} ({last[:120]})")
    return "PASS" if reachable else "FAIL"
