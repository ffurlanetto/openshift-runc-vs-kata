"""POL-17 : privilèges effectifs à l'exécution d'un pod conforme (non-root, no_new_privs, caps).

Une policy d'admission ne vaut que si le runtime applique réellement les réglages. Vérifie, vu du
processus : UID ≠ 0, NoNewPrivs = 1, CapEff = 0, seccomp actif, écriture impossible dans /etc.
Avec kata, ces contrôles sont appliqués par l'agent dans la VM invitée.
"""

META = {"id": "POL-17", "category": "POL", "aspect": "SEC", "priority": "P1",
        "title": "Privilèges effectifs d'un pod conforme", "runs": 1}

SCRIPT = r"""
echo "uid=$(id -u)"
grep -E '^(NoNewPrivs|CapEff|CapPrm|Seccomp):' /proc/self/status | tr -d '\t' | sed 's/:/=/'
if touch /etc/kvr-test 2>/dev/null; then echo "etc_writable=1"; else echo "etc_writable=0"; fi
"""


def run(ctx):
    ctx.apply_template("policy-pod.yaml.j2", name="priv")
    ctx.wait("pod/priv", timeout_s=240)
    rc, out, err = ctx.exec("priv", ["bash", "-c", SCRIPT])
    assert rc == 0, f"script en échec : {err}"
    vals = dict(line.split("=", 1) for line in out.split() if "=" in line)
    ctx.evidence("privileges.txt", out)
    checks = {
        "uid_non_root": vals.get("uid") != "0",
        "no_new_privs": vals.get("NoNewPrivs") == "1",
        "no_effective_caps": int(vals.get("CapEff", "1"), 16) == 0,
        "seccomp_filter": vals.get("Seccomp") == "2",
        "etc_read_only": vals.get("etc_writable") == "0",
    }
    for name, ok in checks.items():
        ctx.metric(name, int(ok), "bool", "higher")
    failed = [k for k, v in checks.items() if not v]
    ctx.observe(f"{vals} ; écarts : {failed or 'aucun'}")
    return "FAIL" if failed else "PASS"
