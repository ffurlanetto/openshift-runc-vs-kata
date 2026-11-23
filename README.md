# OpenShift : runc vs Kata Containers

Campagne d'évaluation comparative des deux modèles d'exécution de pods sur OpenShift :

- **runc** : runtime par défaut de CRI-O, conteneurs partageant le noyau du nœud ;
- **Kata Containers** : chaque pod dans une micro-VM dédiée (OpenShift Sandboxed Containers / kata-deploy).

Volets évalués : **fonctionnel, performance, sécurité, exploitation**, ainsi que deux cas d'usage cibles :
- **CI dans Kata** : pipelines Jenkins et GitHub Actions avec Docker-in-Docker (compilation, tests, packaging, `docker build`) ;
- **agents IA autonomes** : exécution de code généré par un LLM dans des sandboxes isolées (Agent Sandbox).

## Statut

| Phase | Statut |
|---|---|
| Plan de tests (113 tests, dont 73 P1) | ✅ v0.1, en revue |
| Format de rapport | ✅ v0.1 |
| Environnement A (OpenShift Local arm64, nested virt) | 🟡 en préparation |
| Environnement B (OpenShift x86_64 bare metal + OSC) | ⏳ à provisionner |
| Exécution des tests | ⏳ |
| Rapport comité | ⏳ |

## Documents

| Fichier | Contenu |
|---|---|
| [01-ENVIRONNEMENT.md](01-ENVIRONNEMENT.md) | État des lieux, outils, prérequis, contournements |
| [02-PLAN-DE-TESTS.md](02-PLAN-DE-TESTS.md) | Méthodologie et catalogue des tests |
| [03-FORMAT-RAPPORT.md](03-FORMAT-RAPPORT.md) | Format des résultats et structure du rapport comité |
| [schemas/result.schema.json](schemas/result.schema.json) | Schéma JSON d'un résultat brut |

## Arborescence

```
├── 01-ENVIRONNEMENT.md, 02-PLAN-DE-TESTS.md, 03-FORMAT-RAPPORT.md
├── schemas/      # schéma des résultats
├── scripts/      # check-env.sh, validate_results.py, (à venir) run-test.sh, aggregate.py, render-report.py
├── images/       # Containerfiles des images d'outillage (kata-bench, agent-sandbox)
├── ci/           # Jenkins / ARC : values Helm, podTemplates, workflows de référence
├── harness/      # harnais « agent rejoué » (séquences d'appels d'outils)
├── tests/<ID>/   # manifestes et procédure de chaque test
├── results/<ENV>/<ID>/<runtime>/run-<n>.json   # résultats bruts
├── evidence/     # preuves (sorties de commandes, YAML), voir règles ci-dessous
└── report/       # rapport généré (md / html / pdf) et graphiques
```

## Reproduire

```bash
brew install yq k6 hey trivy kubescape pandoc
uv sync
scripts/check-env.sh                 # inventaire et prérequis
uv run scripts/validate_results.py   # valide tous les results/**/*.json
```

## Règles de publication

Ce dépôt est destiné à être partagé. Avant chaque commit de résultats :

1. **Aucun secret** : tokens GitHub/ARC, mots de passe kubeadmin, clés API LLM, identifiants de registre, kubeconfig. Le `.gitignore` en exclut une partie, mais la relecture reste obligatoire.
2. **Anonymiser** les noms d'hôtes, IP, noms de clusters et de dépôts internes de l'entreprise dans `evidence/`.
3. **Pas de code ni de données propriétaires** : les projets de référence internes sont décrits, pas copiés.
4. **Volume** : pas de fichier > 5 Mo dans `evidence/`. Les archives volumineuses (must-gather, traces) vont en pièce jointe d'une *release*.
5. Chaque résultat doit passer `uv run scripts/validate_results.py` (vérifié par la CI sur chaque PR).
6. Le rapport comité est publié sous forme de **release** taguée (`report-vX.Y`) avec le PDF en pièce jointe.

Les scénarios de sécurité décrits ici sont exécutés **uniquement sur des environnements de test dédiés**. Le dépôt ne contient pas d'exploits : seulement des vérifications de surface d'attaque et de confinement.
