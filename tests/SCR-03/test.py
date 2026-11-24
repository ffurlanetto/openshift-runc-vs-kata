"""SCR-03 : token de ServiceAccount projeté, rotation par le kubelet et propagation au conteneur.

Token projeté (audience de l'API server, `expirationSeconds: ttl_s`, 600 minimum). Le kubelet le renouvelle
à 80 % de sa durée de vie. On vérifie que le fichier vu par le conteneur change, et que le nouveau
token est accepté par l'API server (200 ou 403 = authentifié ; 401 = rejeté). /apis est ouvert à tout
utilisateur authentifié (rôle system:discovery) : 200 est la réponse normale.
C'est le mécanisme d'authentification de Vault (`kubernetes`/`jwt`) et de Conjur (`authn-jwt`).
Les preuves ne contiennent que les claims non sensibles (iat, exp, aud), jamais le token.
"""

import base64
import json
import time

META = {"id": "SCR-03", "category": "SCR", "aspect": "FUN", "priority": "P1",
        "title": "Token de ServiceAccount projeté : rotation", "runs": 2, "warmup": False,
        "params": {"ttl_s": 600, "poll_s": 15}}

API = "https://kubernetes.default.svc/apis"
ACCEPTED = ("200", "403")  # 401 = token rejeté


def _claims(token: str) -> dict:
    payload = token.split(".")[1]
    c = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    return {"iat": c.get("iat"), "exp": c.get("exp"), "aud": c.get("aud")}


def _probe(ctx) -> tuple[dict, str]:
    script = (f"t=$(cat /var/run/kvr-token/token); echo \"$t\" | cut -d. -f2; "
              f"curl -sk -o /dev/null -w '%{{http_code}}' --max-time 10 -H \"Authorization: Bearer $t\" {API}")
    rc, out, err = ctx.exec("consumer", ["sh", "-c", script])
    lines = out.split()
    assert rc == 0 and len(lines) == 2, f"lecture du token en échec : {err.strip()[:200]}"
    return _claims("x." + lines[0] + ".y"), lines[1]


def run(ctx):
    ttl, poll = int(ctx.params["ttl_s"]), float(ctx.params["poll_s"])
    ctx.apply_template("secret-pod.yaml.j2", name="consumer", sa_token={"ttl": ttl})
    ctx.wait("pod/consumer", timeout_s=240)
    first, code0 = _probe(ctx)
    t0 = time.perf_counter()
    history = [{"t": 0, **first, "http": code0}]
    rotated, code1 = None, None
    while time.perf_counter() - t0 < ttl * 1.1:
        time.sleep(poll)
        claims, code = _probe(ctx)
        history.append({"t": round(time.perf_counter() - t0), **claims, "http": code})
        if claims["iat"] != first["iat"]:
            rotated, code1 = claims, code
            break
    ctx.evidence("claims.json", history)
    lifetime = (first["exp"] - first["iat"]) if first["exp"] and first["iat"] else None
    ctx.metric("api_accepts_initial_token", int(code0 in ACCEPTED), "bool", "higher")
    if rotated:
        # âge du token au moment où le conteneur voit le nouveau (attendu ≈ 80 % de la durée de vie)
        age = rotated["iat"] - first["iat"]
        ctx.metric("rotation_after", age, "s", "lower")
        ctx.metric("api_accepts_rotated_token", int(code1 in ACCEPTED), "bool", "higher")
    ctx.observe(f"{ctx.runtime} : token initial (durée {lifetime} s, aud {first['aud']}) → HTTP {code0} ; "
                + (f"nouveau token (émis {rotated['iat'] - first['iat']} s après le premier) vu dans le conteneur "
                   f"(sondage toutes les {poll:.0f} s), HTTP {code1}" if rotated else f"AUCUNE rotation vue en {ttl * 1.1:.0f} s"))
    if not rotated:
        return "FAIL"
    return "PASS" if code0 in ACCEPTED and code1 in ACCEPTED else "FAIL"
