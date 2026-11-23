# OpenShift : runc vs Kata Containers

Campagne d'évaluation comparative des deux modèles d'exécution de pods sur OpenShift (et Kubernetes) :

- **runc** : runtime par défaut, conteneurs partageant le noyau du nœud ;
- **Kata Containers** : chaque pod dans une micro-VM dédiée (OpenShift Sandboxed Containers / kata-deploy).

Volets évalués : **fonctionnel, performance, sécurité, policies d'admission (Kyverno), exploitation**, plus deux cas d'usage cibles :
- **CI dans Kata** : pipelines Jenkins et GitHub Actions avec Docker-in-Docker (compilation, tests, packaging, `docker build`) ;
- **agents IA autonomes** : exécution de code généré par un LLM dans des sandboxes isolées (Agent Sandbox).

## Statut

| Phase | Statut |
|---|---|
| Plan de tests : 161 tests, dont 109 P1 (VOL et SCR ajoutés) | ✅ v0.2, en revue |
| Format de rapport | ✅ v0.2 |
| Banc automatisé (`./precheck`, `./run`, `./setup`) | ✅ 23 tests automatisés (FUN, PERF, SEC, POL) |
| Environnement A (OpenShift Local arm64, nested virt) | ✅ Kata 4.4.0 + Kyverno 1.20.0 opérationnels |
| Environnement B (OpenShift x86_64 bare metal + OSC) | ⏳ à provisionner |
| Exécution des tests | 🟡 ENV-A : 23 tests, voir [RESULTATS-ENV-A.md](RESULTATS-ENV-A.md) |
| Rapport comité | ⏳ |

## Documents

| Fichier | Contenu |
|---|---|
| [01-ENVIRONNEMENT.md](01-ENVIRONNEMENT.md) | Prérequis, état des environnements, site airgappé |
| [02-PLAN-DE-TESTS.md](02-PLAN-DE-TESTS.md) | Méthodologie et catalogue des tests |
| [03-FORMAT-RAPPORT.md](03-FORMAT-RAPPORT.md) | Format des résultats et structure du rapport comité |
| [tests/README.md](tests/README.md) | Écrire un test automatisé |

## Utilisation

Prérequis du poste : `bash`, `git`, `kubectl`, `uv`, plus `helm` pour `./setup`. `oc` n'est pas nécessaire.

```bash
./precheck                          # choisir le contexte kube dans la liste, puis contrôle de tous les prérequis
./run                               # precheck + campagne complète (confirmation de la cible demandée)
./run --phases FUN,SEC,POL          # seulement certaines phases (FUN PERF SEC POL OPS DIND AGT VOL SCR)
./run --skip PERF                   # toutes les phases sauf…
./run --tests PERF-01 --runs 10     # tests précis
./run --priority P1 --runtimes runc # sous-ensemble
./run --dry-run                     # affiche le plan d'exécution
./run --list                        # tests automatisés disponibles
./run --replay results/<campagne>/campaign.json [--strict]   # rejeu à l'identique
./run --print-images                # images et charts à mirrorer (site airgappé)
./run --cleanup                     # supprime les namespaces du banc restants
./run --allow-destructive           # exécute aussi les scénarios pouvant faire tomber un nœud (cluster jetable)
./setup kyverno                     # installe Kyverno sur un cluster de TEST (ne touche pas un Kyverno existant)
```

Mode non interactif (CI) : `./run --context <ctx> --env-id ENV-B --yes …`

### Ce que vérifie `./precheck`

- **Outils** : kubectl (et l'écart de version avec le serveur), git propre, images épinglées par digest, helm si nécessaire.
- **Accès et droits** : RBAC et SCC nécessaires (`kubectl auth can-i`).
- **Cluster** :
  - nœuds Ready et sans pression de ressources ;
  - RuntimeClass Kata ;
  - Metrics API ;
  - APIServices en panne ;
  - namespaces résiduels.
- **Registre** : règles miroir, secret de pull, **pull réel de chaque image**.
- **Kyverno** : présence, version, type d'API, ClusterPolicies déjà en Enforce.
- **Admission** : est-ce que les pods du banc passent les policies existantes du cluster ?
- **Smoke test** : un vrai pod par runtime (démarrage, exec, noyau vu).

### Reproductibilité

Chaque campagne enregistre dans `results/<campagne>/campaign.json` :
- le commit git ;
- la configuration complète ;
- les images résolues ;
- le plan d'exécution ;
- l'empreinte du cluster (versions, nœuds, RuntimeClass, Kyverno) ;
- le rapport de precheck.

Les mécanismes qui garantissent la reproductibilité :
- **Arbre git propre** : `./run` refuse de démarrer si le dépôt a des modifications non commitées.
- **Ordre d'exécution** : alterné runc/kata à chaque run (ABAB), avec un run de warm-up.
- **Isolation** : chaque exécution tourne dans un namespace neuf.
- **Comparabilité** : le hash `manifest_sha256` prouve que runc et kata ont reçu le même manifeste, à la ligne `runtimeClassName` près.
- **Rejeu** : `--replay` rejoue le même plan avec les mêmes images et paramètres, et liste tout écart de code ou d'environnement.

## Arborescence

```
├── precheck, run, setup        # points d'entrée
├── campaign.yaml               # profils de clusters, registre/miroir, images, charts, paramètres
├── 01-…, 02-…, 03-….md         # environnement, plan de tests, format de rapport
├── schemas/                    # schéma JSON des résultats
├── scripts/kvr/                # moteur : cluster, cible, precheck, runner, registre, kyverno
├── policies/kyverno/           # catalogue de policies (rendu CEL ou kyverno.io/v1)
├── tests/<ID>/test.py          # un dossier par test automatisé ; tests/_templates/ partagés
├── results/<campagne>/<ENV>/<ID>/<runtime>/run-<n>.json
└── evidence/<campagne>/…       # preuves : manifestes appliqués, sorties, events, policies
```

## Règles de publication

Ce dépôt est destiné à être partagé. Avant chaque commit de résultats :

1. **Aucun secret** : tokens, mots de passe, clés API LLM, identifiants de registre, kubeconfig. Le `.gitignore` en exclut une partie, et gitleaks tourne en CI, mais la relecture reste obligatoire.
2. **Anonymiser** les noms d'hôtes, IP, noms de clusters, URL de miroir et dépôts internes dans `evidence/` et `results/`.
3. **Pas de code ni de données propriétaires** : les projets de référence internes sont décrits, pas copiés.
4. **Volume** : pas de fichier de plus de 5 Mo dans `evidence/`. Les archives volumineuses vont en pièce jointe d'une *release*.
5. Chaque résultat doit passer `uv run scripts/validate_results.py` (vérifié par la CI).
6. Le rapport comité est publié sous forme de **release** taguée `report-vX.Y`.

Les scénarios de sécurité sont exécutés **uniquement sur des environnements de test dédiés**. Le dépôt ne contient pas d'exploits : seulement des vérifications de surface d'attaque et de confinement.
