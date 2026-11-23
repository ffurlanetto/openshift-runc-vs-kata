"""DIND-05 : étape Dockerfile du pipeline (V1 à V4).

Dockerfile multi-étapes de référence : image de base du banc (miroir appliqué), --build-arg,
secret de build (--secret, jamais écrit dans l'image), artefact de 20 Mio. Build à froid puis à
chaud (cache), puis vérification de l'image produite.
"""

from kvr import dind

META = {"id": "DIND-05", "category": "DIND", "aspect": "FUN", "priority": "P1",
        "title": "Build Dockerfile multi-étapes (build-arg, secret, cache)", "variants": dind.VARIANTS, "runs": 3}


def run(ctx):
    dind.deploy(ctx)
    dind.wait_engine(ctx)
    ok_cold, cold, out = dind.build(ctx, "froid")
    if not ok_cold:
        ctx.observe(f"{ctx.variant} : build en échec : {out[-300:]}")
        return "FAIL"
    ok_warm, warm, _ = dind.build(ctx, "chaud")
    ok_img, img = dind.verify_image(ctx)
    ctx.evidence("image.txt", img)
    ctx.metric("build_cold", round(cold, 1), "s", "lower")
    ctx.metric("build_warm", round(warm, 1), "s", "lower")
    ctx.metric("image_verified", int(ok_img), "bool", "higher")
    ctx.observe(f"{ctx.variant} : build froid {cold:.1f}s, chaud {warm:.1f}s, image {'OK' if ok_img else 'KO'}")
    return "PASS" if ok_warm and ok_img else "PARTIAL"
