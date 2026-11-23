"""Aides pour la phase SCR : secrets de test (valeurs factices, déterministes) et lecture dans un pod.

Les valeurs sont générées à partir d'une graine : runc et kata reçoivent exactement les mêmes octets.
Les preuves ne contiennent que des empreintes sha256, jamais les valeurs.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shlex

from .context import TestContext


def fake_bytes(seed: str, size: int) -> bytes:
    """Octets pseudo-aléatoires déterministes (chaîne sha256), y compris non imprimables."""
    out, block = bytearray(), hashlib.sha256(seed.encode()).digest()
    while len(out) < size:
        out += block
        block = hashlib.sha256(block).digest()
    return bytes(out[:size])


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def create_secret(ctx: TestContext, name: str, data: dict[str, bytes], immutable: bool = False,
                  verb: str = "create") -> dict[str, str]:
    """Crée (ou remplace avec verb="replace") un Secret Opaque. Retourne {clé: sha256}.
    Le manifeste n'est pas archivé (taille, et ce sont des données) : seules les empreintes le sont."""
    obj = {"apiVersion": "v1", "kind": "Secret", "type": "Opaque",
           "metadata": {"name": name, "namespace": ctx.namespace, "labels": {"app.kubernetes.io/part-of": "kvr"}},
           "data": {k: base64.b64encode(v).decode() for k, v in data.items()}}
    if immutable:
        obj["immutable"] = True
    ctx.oc(verb, "-n", ctx.namespace, "-f", "-", input=json.dumps(obj))
    digests = {k: sha(v) for k, v in data.items()}
    ctx.evidence(f"secret-{name}-{verb}.json", {"keys": digests, "sizes": {k: len(v) for k, v in data.items()},
                                                 "immutable": immutable})
    return digests


def file_digests(ctx: TestContext, pod: str, paths: list[str], timeout_s: int = 60) -> dict[str, str]:
    """{chemin: sha256 | 'absent'} vus dans le conteneur (une seule commande exec)."""
    script = "; ".join(f"if [ -r {shlex.quote(p)} ]; then sha256sum < {shlex.quote(p)} | cut -c1-64; "
                       f"else echo absent; fi" for p in paths)
    rc, out, err = ctx.exec(pod, ["sh", "-c", script], timeout_s=timeout_s)
    lines = out.split()
    if rc != 0 or len(lines) != len(paths):
        raise AssertionError(f"lecture des fichiers en échec (rc={rc}) : {err.strip()[:200]}")
    return dict(zip(paths, lines))
