"""Moteurs de build CI (phase DIND) : démarrage, informations, build du Dockerfile de référence.

Une variante = un moteur, avec les mêmes manifestes pour runc et kata (template dind-pod.yaml.j2).
"""

from __future__ import annotations

import time

from .cluster import OcError
from .context import Blocked, NotSupported, TestContext

VARIANTS = ["V1-dind-privileged", "V2-dind-rootless", "V3-buildah", "V4-buildkit-rootless",
            "V5-dind-privileged-memstore"]
DOCKER_VARIANTS = ["V1-dind-privileged", "V2-dind-rootless", "V5-dind-privileged-memstore"]
POD = "ci"
CONTAINER = "engine"


def short(variant: str) -> str:
    """Famille du moteur : V5 (dind en mémoire) se pilote comme V1."""
    v = variant.split("-")[0]
    return "V1" if v == "V5" else v


def deploy(ctx: TestContext, timeout_s: int = 300) -> float:
    """Crée le pod de CI ; retourne le délai jusqu'à Ready (s). Le pod tourne en privilégié pour V1/V2 :
    la SCC privileged est accordée au ServiceAccount du namespace (même politique runc/kata)."""
    if not ctx.variant:
        raise Blocked("test DIND lancé sans variante (META['variants'])")
    ctx.grant_scc("privileged")
    t0 = time.perf_counter()
    ctx.apply_template("dind-pod.yaml.j2", variant=ctx.variant)
    ctx.wait(f"pod/{POD}", timeout_s=timeout_s)
    return time.perf_counter() - t0


def sh(ctx: TestContext, script: str, timeout_s: int = 600) -> tuple[int, str, str]:
    return ctx.exec(POD, ["sh", "-c", script], container=CONTAINER, timeout_s=timeout_s)


def wait_engine(ctx: TestContext, timeout_s: int = 300) -> float:
    """Attend que le moteur réponde. V1/V2 : démon dockerd. V3 : buildah (sans démon). V4 : buildkitd rootless
    démarré à la demande par buildctl-daemonless.sh. Retourne le délai en secondes."""
    probe = {
        "V1": "docker info >/dev/null 2>&1",
        "V2": "docker info >/dev/null 2>&1",
        "V3": "buildah info >/dev/null 2>&1",
        "V4": "buildctl-daemonless.sh debug workers >/dev/null 2>&1",
    }[short(ctx.variant)]
    t0 = time.perf_counter()
    last = ""
    while time.perf_counter() - t0 < timeout_s:
        try:
            rc, out, err = sh(ctx, probe + " && echo ok", timeout_s=60)
        except OcError as e:  # exec bloqué (VM lente en imbriqué) : on réessaie jusqu'à timeout_s
            rc, out, err = 1, "", str(e)
        if rc == 0 and "ok" in out:
            return time.perf_counter() - t0
        last = err or out
        time.sleep(2)
    ctx.evidence("engine-logs.txt", ctx.cluster.oc("logs", "-n", ctx.namespace, POD, "-c", CONTAINER,
                                                   "--tail=80", check=False).stdout)
    raise NotSupported(f"moteur {ctx.variant} indisponible après {timeout_s}s : {last.strip()[-300:]}")


def info(ctx: TestContext) -> dict:
    v = short(ctx.variant)
    if v in ("V1", "V2"):
        rc, out, _ = sh(ctx, "docker info --format '{{.Driver}}|{{.CgroupVersion}}|{{.ServerVersion}}|{{.SecurityOptions}}'")
        driver, cgroup, version, secopts = (out.strip().split("|") + ["", "", "", ""])[:4]
        return {"storage_driver": driver, "cgroup_version": cgroup, "engine_version": version, "security": secopts}
    if v == "V3":
        _, out, _ = sh(ctx, "buildah version --json 2>/dev/null | sed -n 's/.*\"version\": *\"\\([^\"]*\\)\".*/\\1/p' | head -1; "
                            "buildah info --format '{{.store.GraphDriverName}}' 2>/dev/null")
        lines = out.strip().splitlines() + ["", ""]
        return {"engine_version": lines[0], "storage_driver": lines[1]}
    _, out, _ = sh(ctx, "buildkitd --version 2>/dev/null | awk '{print $3}'")
    return {"engine_version": out.strip(), "storage_driver": "overlayfs/native (buildkit)"}


def build_command(ctx: TestContext, tag: str = "kvr/demo") -> str:
    base = ctx.images["ubi_minimal"]
    args = f"--build-arg BASE={base} --build-arg GREETING=kvr"
    v = short(ctx.variant)
    if v in ("V1", "V2"):
        return f"docker build -q {args} --secret id=token,src=/work/secret.txt -t {tag} /work"
    if v == "V3":
        return f"buildah build -q {args} --secret id=token,src=/work/secret.txt -t {tag} /work"
    return ("buildctl-daemonless.sh build --frontend dockerfile.v0 --local context=/work --local dockerfile=/work "
            f"--opt build-arg:BASE={base} --opt build-arg:GREETING=kvr "
            "--secret id=token,src=/work/secret.txt --output type=oci,dest=/tmp/demo.tar")


def build(ctx: TestContext, label: str) -> tuple[bool, float, str]:
    """Build du Dockerfile de référence ; retourne (succès, durée s, sortie)."""
    t0 = time.perf_counter()
    rc, out, err = sh(ctx, build_command(ctx) + " 2>&1", timeout_s=900)
    duration = time.perf_counter() - t0
    ctx.evidence(f"build-{label}.txt", f"$ {build_command(ctx)}\nrc={rc}\n{out}{err}")
    return rc == 0, duration, (out + err).strip()


def verify_image(ctx: TestContext) -> tuple[bool, str]:
    """L'image produite contient bien l'artefact de la première étape (build-arg + secret consommé)."""
    v = short(ctx.variant)
    if v in ("V1", "V2"):
        rc, out, err = sh(ctx, "docker run --rm kvr/demo", timeout_s=180)
        return rc == 0 and "greeting=kvr" in out, (out + err).strip()
    if v == "V3":
        rc, out, err = sh(ctx, "buildah images --format '{{.Name}}:{{.Tag}} {{.Size}}' | grep kvr/demo")
        return rc == 0 and "kvr/demo" in out, (out + err).strip()
    rc, out, err = sh(ctx, "tar -tf /tmp/demo.tar | grep -c -e index.json -e blobs/")
    return rc == 0 and out.strip() not in ("", "0"), (out + err).strip()
