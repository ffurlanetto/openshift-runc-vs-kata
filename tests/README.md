# Écrire un test automatisé

Un test = un dossier `tests/<ID>/` (ID du plan, ex. `SEC-04`) contenant `test.py` et, si besoin, ses templates Jinja.
Les templates partagés sont dans `tests/_templates/` :
- `probe-pod.yaml.j2` : pod restreint qui dort ;
- `policy-pod.yaml.j2` : pod « bonnes pratiques » avec écarts paramétrables, en Pod ou en Deployment ;
- `secret-pod.yaml.j2` : pod consommateur de secrets (volumes, `items`, projeté, `subPath`, env, token projeté) ;
- `pvc-pod.yaml.j2` : PVC + pod restreint qui la monte sur `/data` ;
- `host-reader-pod.yaml.j2` : pod privilégié en lecture seule sur l'hôte (vue du nœud, pod compromis) ;
- `dind-pod.yaml.j2` : pod de CI avec moteur de build (variantes V1 à V5).

Ces templates acceptent `rc` (`"runc"` ou une RuntimeClass) pour forcer le runtime d'un pod annexe
(victime, vue du nœud), et `node_name` pour le placer sur le même nœud que le pod testé.

```python
META = {
    "id": "SEC-04",            # = nom du dossier
    "category": "SEC",         # phase : FUN PERF SEC POL OPS DIND AGT VOL SCR
    "aspect": "SEC",           # FUN | PERF | SEC | OPS (obligatoire pour DIND/AGT/VOL/SCR)
    "priority": "P1",
    "title": "…",
    "runs": 1,                 # optionnel (défaut : campaign.yaml › defaults.runs)
    "warmup": False,           # optionnel : pas de run 0 de warm-up
    "params": {…},             # optionnel, surchargeable dans campaign.yaml › overrides.<ID>.params
}


def run(ctx):
    ctx.apply_template("probe-pod.yaml.j2")          # rendu + archivage + kubectl create
    ctx.wait("pod/probe")                            # oc wait ; Blocked si non planifiable
    rc, out, err = ctx.exec("probe", ["uname", "-r"])
    ctx.metric("nom_metrique", 42, "ms", "lower")    # unité + sens obligatoires
    ctx.observe("constat lisible par le comité")
    ctx.evidence("sortie.txt", out)                  # preuve brute
    return "PASS"                                    # PASS FAIL PARTIAL NOT_SUPPORTED BLOCKED N/A
```

Règles :
- **Le manifeste ne dépend du runtime que par `runtime_class`**. Les templates reçoivent :
  - `namespace`, `runtime_class` (None pour runc), `platform` (openshift/kubernetes) ;
  - `node_selector`, `images` (déjà réécrites vers le miroir), `params`.
- **Jamais d'image en dur** : toute image passe par `campaign.yaml › images`, épinglée par digest.
- `raise Blocked("…")` pour un prérequis d'environnement manquant ; `raise NotSupported("…")` pour une limite constatée du runtime ; `assert` pour un échec.
- **Pas de nettoyage dans le test** : le runner supprime les pods puis le namespace, et collecte `pods.json` et `events.txt`.
- Pour les policies Kyverno :
  - `from kvr.policy_tests import admission_matrix` pour une règle de validation ;
  - `kvr.kyverno.apply_policy(ctx, "<id du catalogue>")` pour un cas spécifique.
- Vérifier sans cluster : `./run --dry-run --tests <ID>`. Le rendu des templates se teste en Python, comme dans le commit qui a introduit POL.
