"""SEC-08 : quelle surface du noyau un pod restreint peut-il atteindre ?

Pod restreint (non-root, `drop: ALL`, `allowPrivilegeEscalation: false`, seccomp `RuntimeDefault`) dans le
runtime du run. Chaque appel système sensible est fait dans un processus enfant, avec des arguments sans
effet (descripteur invalide, pointeur nul, horloge non réglable…), et on relève le résultat :
- « bloqué » : EPERM / EACCES / ENOSYS (seccomp, capacité absente ou appel indisponible) ;
- « atteint » : le noyau a traité l'appel (succès, ou erreur d'argument EINVAL / EFAULT / EBADF…).
Aucun appel n'a d'effet : pas de module chargé, pas d'horloge modifiée, pas de montage.

Lecture : en runc, « atteint » = noyau du NŒUD exposé ; en kata, noyau de la VM. On relève aussi le mode
seccomp effectif (`Seccomp:` de /proc/self/status) : 2 = filtre actif.
Statut : PASS si le filtre seccomp est actif ; PARTIAL s'il ne l'est pas (constat ENV-A pour Kata Rust).
"""

from kvr import escape

META = {"id": "SEC-08", "category": "SEC", "aspect": "SEC", "priority": "P1",
        "title": "Surface noyau atteignable depuis un pod restreint", "runs": 2}

PROBE = r"""
import ctypes, errno, json, os, platform
libc = ctypes.CDLL(None, use_errno=True)
arch = 0 if platform.machine() in ("x86_64", "amd64") else 1
NR = json.loads(os.environ["KVR_NR"])
buf = ctypes.create_string_buffer(256)
null = ctypes.c_void_p(0)
CALLS = {
  "unshare":          lambda n: libc.syscall(n, 0x10000000),
  "setns":            lambda n: libc.syscall(n, -1, 0),
  "keyctl":           lambda n: libc.syscall(n, 0, -3, 0),
  "add_key":          lambda n: libc.syscall(n, b"user", b"kvr", b"x", 1, -2),
  "bpf":              lambda n: libc.syscall(n, 0, null, 0),
  "userfaultfd":      lambda n: libc.syscall(n, 0),
  "io_uring_setup":   lambda n: libc.syscall(n, 1, buf),
  "ptrace":           lambda n: libc.syscall(n, 0, 0, 0, 0),
  "perf_event_open":  lambda n: libc.syscall(n, null, 0, -1, -1, 0),
  "mount":            lambda n: libc.syscall(n, b"none", b"/tmp", b"tmpfs", 0, null),
  "open_by_handle_at":lambda n: libc.syscall(n, -100, null, 0),
  "init_module":      lambda n: libc.syscall(n, null, 0, b""),
  "kexec_load":       lambda n: libc.syscall(n, 0, 0, null, 0),
  "clock_settime":    lambda n: libc.syscall(n, 1, buf),
  "pivot_root":       lambda n: libc.syscall(n, null, null),
  "chroot":           lambda n: libc.syscall(n, b"/"),
  "swapon":           lambda n: libc.syscall(n, null, 0),
  "syslog":           lambda n: libc.syscall(n, 10, null, 0),
}
out = {}
for name, call in CALLS.items():
    r, w = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(r)
        ret = call(NR[name][arch]); e = ctypes.get_errno()
        os.write(w, json.dumps([ret, e]).encode()); os._exit(0)
    os.close(w)
    data = os.read(r, 256); os.close(r); _, st = os.waitpid(pid, 0)
    if not data:
        out[name] = {"result": "tué", "detail": f"statut {st}"}
        continue
    ret, e = json.loads(data)
    if ret >= 0:
        out[name] = {"result": "atteint", "detail": "succès"}
    elif e in (errno.EPERM, errno.EACCES, errno.ENOSYS):
        out[name] = {"result": "bloqué", "detail": errno.errorcode.get(e, str(e))}
    else:
        out[name] = {"result": "atteint", "detail": errno.errorcode.get(e, str(e))}
status = dict(l.split(":", 1) for l in open("/proc/self/status") if ":" in l)
print(json.dumps({"calls": out, "seccomp": status.get("Seccomp", "?").strip(),
                  "no_new_privs": status.get("NoNewPrivs", "?").strip(), "kernel": platform.release(),
                  "uid": os.getuid()}))
"""


def run(ctx):
    import json
    escape.deploy(ctx, "restricted", run_as_user=1001, allow_pe=False, drop_all=True, seccomp="RuntimeDefault",
                  env=[{"name": "KVR_NR", "value": json.dumps(escape.SYSCALLS)}], memory="384Mi")
    res = escape.run_py(ctx, "restricted", PROBE, timeout_s=120)
    ctx.evidence("syscalls.json", res)
    calls = res["calls"]
    reached = sorted(n for n, c in calls.items() if c["result"] == "atteint")
    blocked = sorted(n for n, c in calls.items() if c["result"] == "bloqué")
    ctx.metric("syscalls_reached", len(reached), "count", "lower")
    ctx.metric("syscalls_blocked", len(blocked), "count", "higher")
    seccomp_on = res["seccomp"] == "2"
    ctx.metric("seccomp_filter_active", int(seccomp_on), "bool", "higher")
    kernel = "du NŒUD" if ctx.runtime == "runc" else "de la VM"
    ctx.observe(f"{ctx.runtime} : seccomp={res['seccomp']} ({'filtre actif' if seccomp_on else 'AUCUN filtre'}), "
                f"NoNewPrivs={res['no_new_privs']}, uid={res['uid']}, noyau {res['kernel']} ({kernel}) ; "
                f"{len(reached)}/{len(calls)} appels atteignent le noyau {kernel} : "
                + ", ".join(f"{n}({calls[n]['detail']})" for n in reached)
                + f" ; bloqués : {', '.join(blocked) or 'aucun'}")
    return "PASS" if seccomp_on else "PARTIAL"
