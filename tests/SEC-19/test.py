"""SEC-19 : escalade de privilèges à l'intérieur du pod — les garde-fous sont-ils appliqués à l'identique ?

Trois pods dans le runtime du run (image ubi), mêmes contrôles :
- « restreint »   : non-root (1001), `allowPrivilegeEscalation: false`, `drop: ALL`, seccomp RuntimeDefault ;
- « root-nnp »    : root, `allowPrivilegeEscalation: false`, capacités par défaut du runtime ;
- « root-escal »  : root, `allowPrivilegeEscalation: true`, capacités par défaut.

Contrôles :
1. état du processus : NoNewPrivs, Seccomp, capacités effectives et bornantes (CapEff / CapBnd), uid_map ;
2. setuid : en root, copie de `id` rendue setuid-root, puis exécution en tant que 1001 (setpriv) : l'uid
   effectif obtenu est-il 0 ? Attendu : NON avec allowPrivilegeEscalation=false (no_new_privs), OUI sinon ;
3. capacités utilisables (root) : mknod, socket brute, chown, montage tmpfs, sethostname ; aucune n'a
   d'effet hors du conteneur (fichiers sous /tmp, montage annulé aussitôt) ;
4. espace de noms utilisateur : `unshare -U -r` depuis le pod restreint (root « fictif » dans un userns).

Lecture : un écart runc / kata = garde-fou appliqué différemment. En kata, root dans le pod = root de la VM,
pas du nœud (voir SEC-04). PASS si aucune escalade n'est possible là où elle est interdite (restreint et
root-nnp) ; FAIL sinon.
"""

from kvr import escape

META = {"id": "SEC-19", "category": "SEC", "aspect": "SEC", "priority": "P1",
        "title": "Escalade de privilèges dans le pod (setuid, capacités, no_new_privs)", "runs": 2}

STATE = r"""
st=/proc/self/status
echo "NNP $(awk '/^NoNewPrivs/{print $2}' $st)"
echo "SECCOMP $(awk '/^Seccomp:/{print $2}' $st)"
echo "CAPEFF $(awk '/^CapEff/{print $2}' $st)"
echo "CAPBND $(awk '/^CapBnd/{print $2}' $st)"
echo "UIDMAP $(awk '{$1=$1; print}' /proc/self/uid_map)"
echo "UID $(id -u)"
"""

ROOT_CHECKS = r"""
cp /usr/bin/id /tmp/kvr-suid-id && chown 0:0 /tmp/kvr-suid-id && chmod 4755 /tmp/kvr-suid-id
echo "SUIDMODE $(stat -c %a /tmp/kvr-suid-id)"
echo "SUIDFS $(stat -f -c %T /tmp) $(awk '$2=="/"{print $4}' /proc/mounts | tr ',' '\n' | grep -c '^nosuid$')"
echo "SETUID_EUID $(setpriv --reuid 1001 --regid 1001 --clear-groups /tmp/kvr-suid-id -u 2>&1)"
echo "CAP_MKNOD $(mknod /tmp/kvr-null c 1 3 2>/dev/null && echo oui || echo non)"
echo "CAP_RAW $(python3 -c 'import socket; socket.socket(socket.AF_INET, socket.SOCK_RAW, 1)' 2>/dev/null && echo oui || echo non)"
echo "CAP_CHOWN $(touch /tmp/kvr-c && chown 1234 /tmp/kvr-c 2>/dev/null && echo oui || echo non)"
mkdir -p /tmp/kvr-m
echo "CAP_MOUNT $(mount -t tmpfs none /tmp/kvr-m 2>/dev/null && { umount /tmp/kvr-m; echo oui; } || echo non)"
echo "CAP_HOSTNAME $(hostname kvr-test 2>/dev/null && echo oui || echo non)"
rm -f /tmp/kvr-suid-id /tmp/kvr-null /tmp/kvr-c
"""

USERNS = r"""echo "USERNS $(unshare -U -r sh -c 'echo uid=$(id -u) capeff=$(awk "/^CapEff/{print \$2}" /proc/self/status)' 2>&1 | head -c 120)" """

CAPS = ["chown", "dac_override", "dac_read_search", "fowner", "fsetid", "kill", "setgid", "setuid", "setpcap",
        "linux_immutable", "net_bind_service", "net_broadcast", "net_admin", "net_raw", "ipc_lock", "ipc_owner",
        "sys_module", "sys_rawio", "sys_chroot", "sys_ptrace", "sys_pacct", "sys_admin", "sys_boot", "sys_nice",
        "sys_resource", "sys_time", "sys_tty_config", "mknod", "lease", "audit_write", "audit_control", "setfcap",
        "mac_override", "mac_admin", "syslog", "wake_alarm", "block_suspend", "audit_read", "perfmon", "bpf",
        "checkpoint_restore"]


def caps(hexmask: str) -> list[str]:
    try:
        v = int(hexmask, 16)
    except ValueError:
        return ["?"]
    return [c for i, c in enumerate(CAPS) if v >> i & 1]


def kv(out: str) -> dict[str, str]:
    return {l.split(" ", 1)[0]: (l.split(" ", 1) + [""])[1].strip() for l in out.splitlines() if l.strip()}


def run(ctx):
    ctx.grant_scc("privileged")  # pods root sans privilège : SCC permettant runAsUser 0 (privileged: false)
    pods = {"restreint": dict(run_as_user=1001, allow_pe=False, drop_all=True, seccomp="RuntimeDefault"),
            "root-nnp": dict(run_as_user=0, allow_pe=False, seccomp="RuntimeDefault"),
            "root-escal": dict(run_as_user=0, allow_pe=True, seccomp="RuntimeDefault")}
    node = None
    res: dict[str, dict] = {}
    for name, sec in pods.items():
        p = escape.deploy(ctx, name, node_name=node, **sec)
        node = node or p["spec"]["nodeName"]
        _, out, _ = escape.run_sh(ctx, name, STATE + (ROOT_CHECKS if sec["run_as_user"] == 0 else USERNS))
        res[name] = kv(out)
        res[name]["caps_eff"] = caps(res[name].get("CAPEFF", ""))
    ctx.evidence("privileges.json", res)

    def euid(name):
        v = res[name].get("SETUID_EUID", "")
        return v if v.isdigit() else f"erreur ({v[:60]})"

    restricted_ok = res["restreint"].get("NNP") == "1" and res["restreint"].get("CAPEFF", "").strip("0") == ""
    nnp_blocks = euid("root-nnp") != "0"
    escal = euid("root-escal") == "0"
    ctx.metric("restricted_caps_effective", len(res["restreint"]["caps_eff"]), "count", "lower")
    ctx.metric("setuid_escalation_blocked_by_nnp", int(nnp_blocks), "bool", "higher")
    ctx.metric("setuid_escalation_when_allowed", int(escal), "bool", "lower")
    ctx.metric("root_caps_effective", len(res["root-nnp"]["caps_eff"]), "count", "lower")
    usable = [c.removeprefix("CAP_").lower() for c in ("CAP_MKNOD", "CAP_RAW", "CAP_CHOWN", "CAP_MOUNT", "CAP_HOSTNAME")
              if res["root-nnp"].get(c) == "oui"]
    ctx.observe(f"{ctx.runtime} : restreint NNP={res['restreint'].get('NNP')} seccomp={res['restreint'].get('SECCOMP')} "
                f"capacités={res['restreint']['caps_eff'] or 'aucune'} userns={res['restreint'].get('USERNS', '?')} ; "
                f"setuid-root lancé par 1001 → euid {euid('root-nnp')} avec allowPrivilegeEscalation=false, "
                f"{euid('root-escal')} avec true (fs {res['root-escal'].get('SUIDFS', '?')}) ; "
                f"root : {len(res['root-nnp']['caps_eff'])} capacités ({', '.join(res['root-nnp']['caps_eff'])}), "
                f"utilisables : {', '.join(usable) or 'aucune'} ; uid_map {res['root-nnp'].get('UIDMAP')}")
    return "PASS" if restricted_ok and nnp_blocks else "FAIL"
