"""AGT-14 : l'agent peut-il atteindre l'API Kubernetes ou des métadonnées ?

Sandbox d'agent durcie : automountServiceAccountToken=false. Vérifie l'absence de token, le refus
de l'API sans identité (401/403) et l'absence de service de métadonnées (169.254.169.254).
Contrôles indépendants du runtime : attendus identiques runc / kata (défense en profondeur).
"""

META = {"id": "AGT-14", "category": "AGT", "aspect": "SEC", "priority": "P1", "agent_mode": "replay",
        "title": "Accès à l'API Kubernetes et aux métadonnées", "runs": 1, "warmup": False}


def run(ctx):
    ctx.apply_template("probe-pod.yaml.j2")
    ctx.wait("pod/probe")
    _, tok, _ = ctx.exec("probe", ["sh", "-c", "ls /var/run/secrets/kubernetes.io/serviceaccount/token 2>/dev/null | wc -l"])
    has_token = tok.strip() not in ("", "0")
    _, api, _ = ctx.exec("probe", ["sh", "-c",
                                   f"curl -sk -o /dev/null -w '%{{http_code}}' --max-time 10 "
                                   f"https://kubernetes.default.svc/api/v1/namespaces/{ctx.namespace}/pods"])
    _, meta, _ = ctx.exec("probe", ["sh", "-c",
                                    "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://169.254.169.254/ || true"])
    api_code, meta_code = api.strip() or "000", meta.strip() or "000"
    api_denied = api_code in ("401", "403")
    meta_blocked = meta_code == "000"
    ctx.metric("sa_token_present", int(has_token), "bool", "lower")
    ctx.metric("api_denied", int(api_denied), "bool", "higher")
    ctx.metric("metadata_unreachable", int(meta_blocked), "bool", "higher")
    ctx.observe(f"token SA présent={has_token} ; API sans identité → HTTP {api_code} ; métadonnées → {meta_code}")
    return "PASS" if not has_token and api_denied and meta_blocked else "FAIL"
