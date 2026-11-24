"""Aides des tests d'isolation et d'évasion (SEC-04/05/08/09/18/19).

Principes communs :
- un « attaquant » tourne dans le runtime du run (runc ou kata) ;
- une « sonde nœud » tourne TOUJOURS en runc (privilégiée si besoin) sur le même nœud : c'est elle qui
  constate l'effet réel sur le nœud. Le constat ne repose jamais sur ce que l'attaquant croit avoir fait ;
- tout ce qui est écrit sur le nœud porte un jeton unique (kvr-<test>-<jeton>) et est supprimé à la fin ;
- toute modification de réglage noyau du nœud est restaurée, et la restauration est vérifiée.
"""

from __future__ import annotations

import base64
import json
import secrets
import shlex

from .context import TestContext

# Numéros d'appels système (x86_64, aarch64) pour les tests qui appellent le noyau directement.
SYSCALLS = {
    "unshare": (272, 97), "setns": (308, 268), "keyctl": (250, 219), "add_key": (248, 217),
    "bpf": (321, 280), "userfaultfd": (323, 282), "io_uring_setup": (425, 425), "ptrace": (101, 117),
    "perf_event_open": (298, 241), "mount": (165, 40), "open_by_handle_at": (304, 265),
    "init_module": (175, 105), "delete_module": (176, 106), "kexec_load": (246, 104),
    "clock_settime": (227, 112), "pivot_root": (155, 41), "chroot": (161, 51), "swapon": (167, 224),
    "syslog": (103, 116),
}


def token() -> str:
    return secrets.token_hex(8)


def deploy(ctx: TestContext, name: str, timeout_s: int = 240, **params) -> dict:
    """Crée un pod depuis sec-pod.yaml.j2, attend qu'il soit prêt, retourne l'objet Pod."""
    ctx.apply_template("sec-pod.yaml.j2", name=name, **params)
    ctx.wait(f"pod/{name}", timeout_s=timeout_s)
    return ctx.get(f"pod/{name}")


def _payload(script: str) -> str:
    return base64.b64encode(script.encode()).decode()


def run_py(ctx: TestContext, pod: str, script: str, *args, timeout_s: int = 300) -> dict:
    """Exécute un script python3 dans le pod ; la dernière ligne de sortie doit être un objet JSON."""
    argv = " ".join(shlex.quote(str(a)) for a in args)
    rc, out, err = ctx.exec(pod, ["sh", "-c", f"echo {_payload(script)} | base64 -d > /tmp/kvr.py && "
                                              f"python3 /tmp/kvr.py {argv}"], timeout_s=timeout_s)
    lines = out.strip().splitlines()
    if rc != 0 or not lines:
        raise AssertionError(f"script python en échec dans {pod} (rc={rc}) : {(err or out).strip()[-300:]}")
    return json.loads(lines[-1])


def run_sh(ctx: TestContext, pod: str, script: str, *args, timeout_s: int = 300) -> tuple[int, str, str]:
    argv = " ".join(shlex.quote(str(a)) for a in args)
    return ctx.exec(pod, ["sh", "-c", f"echo {_payload(script)} | base64 -d > /tmp/kvr.sh && "
                                      f"bash /tmp/kvr.sh {argv}"], timeout_s=timeout_s)


def node_of(ctx: TestContext, pod: str) -> str:
    return ctx.get(f"pod/{pod}")["spec"]["nodeName"]


def lines_with(out: str, prefix: str) -> list[list[str]]:
    """Lignes « PREFIX champ1 champ2 reste… » d'une sortie de script, découpées en 3 champs au plus."""
    return [l.split(maxsplit=3)[1:] for l in out.splitlines() if l.startswith(prefix + " ")]
