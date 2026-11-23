# 03 — Spécification du format de retour (rapport comité)

Objectif : un format **unique, comparable et traçable**. Chaque chiffre du rapport comité doit pouvoir être relié à un fichier de résultat brut.

Trois niveaux :

| Niveau | Fichier | Producteur | Lecteur |
|---|---|---|---|
| 1. Résultat brut d'un run | `results/<campagne>/<ENV>/<ID>/<runtime>/run-<n>.json` (+ `campaign.json` par campagne) | `./run` | Machine (agrégation) |
| 2. Fiche de test (synthèse runc vs kata) | `report/tests/<ID>.md` (générée) | `uv run scripts/aggregate.py` | Équipe technique |
| 3. Rapport comité | `report/rapport-comite.md` → `.html` / `.pdf` (pandoc) | Générée + rédaction humaine | Comité |

---

## 1. Niveau 1 — Résultat brut (JSON)

Validé par `schemas/result.schema.json`. Exemple :

```json
{
  "schema_version": "1.0",
  "test_id": "PERF-01",
  "category": "PERF",
  "title": "Latence de démarrage d'un pod",
  "runtime": "kata",
  "run": 3,
  "env": {
    "id": "ENV-A",
    "platform": "CRC 2.62.0 / OCP 4.22.1",
    "arch": "arm64",
    "node": "crc",
    "context": "crc-admin",
    "nested_virt": true,
    "kata_version": "3.x (kata-deploy)",
    "hypervisor": "qemu",
    "crio_version": "1.35.4"
  },
  "started_at": "2026-11-24T10:12:03Z",
  "duration_s": 4.21,
  "status": "PASS",
  "metrics": [
    {"name": "pod_ready_latency", "value": 1830, "unit": "ms", "better": "lower"}
  ],
  "observations": "Noyau invité 6.12, aucun événement Warning.",
  "evidence": ["evidence/PERF-01/kata/run-3/pod.json", "evidence/PERF-01/kata/run-3/events.txt"],
  "manifest_sha256": "…",
  "operator": "initiales",
  "warmup": false,
  "campaign": {"id": "20261124-101203-ENV-A-1fbd2ad", "git_commit": "…", "git_dirty": false, "replay_of": null}
}
```

Règles :
- `status` ∈ `PASS | FAIL | PARTIAL | NOT_SUPPORTED | BLOCKED | N/A`.
- `aspect` ∈ `FUN | PERF | SEC | OPS`. Obligatoire pour les catégories transverses `DIND`, `AGT`, `VOL` et `SCR`, qui mélangent les trois aspects.
- Pour `DIND` : champs `variant` (`V1-dind-privileged`, `V2-dind-rootless`, `V3-buildah`, `V4-buildkit-rootless`), `ci_platform` (`jenkins`, `github-arc-dind`, `github-arc-k8s`), `project` (`P-JAVA`, `P-NODE`…) et, pour la perf, une métrique par étape du pipeline (`stage_<nom>_duration`, en s).
- Pour `AGT` : champ `agent_mode` (`llm` ou `replay`) ; en mode `llm`, ajouter `llm_model` et `tokens` (in/out) pour séparer le coût LLM du coût runtime.
- Chaque métrique porte son **unité** et son sens (`better: lower|higher`).
- `manifest_sha256` = hash du manifeste appliqué, pour prouver que runc et kata ont reçu le même manifeste (à la ligne `runtimeClassName` près).
- `evidence` : fichiers bruts (sorties de commande, `oc get -o yaml`, captures) conservés dans `evidence/`.

## 2. Niveau 2 — Fiche de test (générée)

```markdown
### PERF-01 — Latence de démarrage d'un pod   [ENV-A · indicatif]

| Métrique | Unité | runc médiane | runc p95 | kata médiane | kata p95 | Δ médiane | Verdict |
|---|---|---|---|---|---|---|---|
| pod_ready_latency | ms | 620 | 710 | 1830 | 2105 | +195 % | ▼ kata plus lent (significatif) |

Statuts : runc PASS (30/30) · kata PASS (30/30)
Observations : …
Preuves : results/ENV-A/PERF-01/
```

Règles de verdict automatique :
- `Δ = (kata − runc) / runc`.
- **Significatif** si |Δ| > 5 % **et** pas de recouvrement des intervalles [p5 ; p95].
- Symboles : ▲ kata meilleur · ▼ kata moins bon · ≈ pas de différence significative.

Pour les tests fonctionnels et sécurité, la fiche contient : statut runc, statut kata, comportement observé, contournement éventuel, preuve.

## 3. Niveau 3 — Rapport comité : structure imposée

1. **Page de garde** : titre, version, date, auteurs, diffusion, statut (brouillon / validé).
2. **Synthèse décisionnelle (1 page max)**
   - Recommandation en une phrase (ex. « Kata pour les workloads multi-tenants non fiables et les builds ; runc par défaut »).
   - 3 à 5 constats clés chiffrés.
   - Décision demandée au comité.
3. **Contexte et périmètre** : objectifs, hors périmètre, environnements (avec l'avertissement sur ENV-A).
4. **Tableau de bord** (§4 ci-dessous).
5. **Résultats par domaine** : Sécurité, Fonctionnel, Performance, Exploitation. Pour chacun : tableau de synthèse, 1 ou 2 graphiques, faits marquants.
6. **Cas d'usage cibles** : une fiche de décision pour **Docker-in-Kata** et une pour les **agents IA autonomes** (§6 bis ci-dessous).
7. **Matrice avantages / inconvénients / limites** (§6 ci-dessous).
8. **Recommandations d'usage** : arbre de décision « quel runtime pour quel workload » + politique d'imposition (qui peut choisir Kata, namespaces concernés).
9. **Risques, prérequis et coûts** : nœuds bare metal, surconsommation, support, compétences.
10. **Limites de l'étude** (*threats to validity*) : nested virt, nœud unique, arm64 vs x86, kata upstream vs OSC, statut *preview* d'Agent Sandbox, non-déterminisme du LLM, échantillons.
11. **Prochaines étapes** : pilote, CoCo, peer-pods, etc.
12. **Annexes** : catalogue complet des tests et statuts, fiches de test, versions exactes, procédures de reproduction.

## 4. Tableau de bord (vue comité)

### 4.1 Couverture et statuts

| Domaine | Tests | runc PASS | kata PASS | kata PARTIAL | kata NOT_SUPPORTED | BLOCKED |
|---|---|---|---|---|---|---|
| Fonctionnel | 30 | | | | | |
| Performance | 16 | | | | | |
| Sécurité | 17 | | | | | |
| Policies d'admission (Kyverno) | 18 | | | | | |
| Exploitation | 10 | | | | | |
| CI dans Kata (DIND) | 20 | | | | | |
| Agents IA | 20 | | | | | |

### 4.2 Indicateurs clés (ENV-B de référence)

| Indicateur | runc | kata | Δ | Lecture |
|---|---|---|---|---|
| Démarrage pod (p50 / p95) | | | | |
| Overhead mémoire par pod | 0 | | | |
| Densité max par nœud | | | | |
| Débit réseau pod-pod | | | | |
| IOPS 4k randread PVC | | | | |
| Latence HTTP p99 @ charge nominale | | | | |
| Scénarios d'évasion réussis (sur N) | | | | |
| Policies Kyverno appliquées à l'identique (sur 10) | | | | |
| Contournements de policy admis (sur 3) | | | | |
| Dépassement de limite CPU / ephemeral-storage à l'exécution | Oui/Non | Oui/Non | | |
| Kata forçable par policy (mutation + overhead appliqué) | — | Oui/Partiel/Non | | |
| Durée pipeline P-JAVA / P-NODE (Jenkins, GitHub) | | | | |
| Étape `docker build` (froid / chaud) | | | | |
| Job en file → runner prêt | | | | |
| Jobs CI simultanés max par nœud | | | | |
| Évasion vers le nœud depuis un job CI malveillant | Oui/Non | Oui/Non | | |
| Sandbox agent prête : à froid / via warm pool | | | | |
| Latence d'un appel d'outil (p50 / p95) | | | | |
| Sandboxes d'agents actives max par nœud | | | | |
| Part du runtime dans la durée d'une tâche agent | | | | |

### 4.3 Notation pondérée

Notes de 1 à 5 par domaine, justifiées par les IDs de test.

| Domaine | Poids | runc | kata | Justification (IDs) |
|---|---|---|---|---|
| Sécurité / isolation | 35 % | | | SEC-04, SEC-06, SEC-14… |
| Compatibilité fonctionnelle | 25 % | | | |
| Performance / coût | 20 % | | | |
| Exploitabilité | 15 % | | | |
| Support / maturité | 5 % | | | |
| **Score pondéré** | 100 % | | | |

## 5. Grille de notation (1 à 5)

| Note | Sécurité | Fonctionnel | Performance | Exploitation |
|---|---|---|---|---|
| 5 | Aucun scénario P1 d'évasion réussi, pas d'angle mort de détection | 100 % P1 PASS sans modification | Δ < 5 % sur tous les indicateurs clés | Identique à l'existant |
| 4 | Évasion seulement en configuration explicitement dangereuse (hostPath /) | ≥ 95 % P1, contournements simples | Δ < 20 % | Écarts mineurs documentés |
| 3 | Évasion possible avec pod privilégié | ≥ 85 % P1 | Δ < 50 % | Outillage complémentaire nécessaire |
| 2 | Évasion possible avec capabilities courantes | ≥ 70 % P1 | Δ < 100 % | Procédures spécifiques lourdes |
| 1 | Évasion depuis un pod restreint | < 70 % P1 | Δ ≥ 100 % | Non exploitable en l'état |

## 6. Matrice avantages / inconvénients / limites (gabarit)

Chaque ligne est **appuyée par au moins un ID de test** ; une affirmation non testée est marquée « (documentaire) ».

| Modèle | Avantages | Inconvénients | Limites (non supporté / contournement) | Cas d'usage recommandés |
|---|---|---|---|---|
| runc | … (IDs) | … (IDs) | … (IDs) | … |
| Kata | … (IDs) | … (IDs) | … (IDs) | … |

## 6 bis. Fiche de décision par cas d'usage (DIND, AGT, VOL, SCR)

Une fiche par cas d'usage, une page maximum :

```markdown
### Cas d'usage : <CI Jenkins / GitHub Actions dans Kata | Agents IA autonomes>

**Verdict** : runc = <recommandé | acceptable avec conditions | déconseillé>
              kata = <recommandé | acceptable avec conditions | déconseillé>

| Aspect | runc | kata | Tests |
|---|---|---|---|
| Fonctionnel | statut + écarts | statut + contournements | DIND-01..09 |
| Performance | chiffres clés | chiffres clés + Δ | DIND-10..13 |
| Sécurité | risque résiduel | risque résiduel | DIND-14..20 |

**Conditions de mise en œuvre** : (ex. politique d'admission « privileged ⇒ kata »,
egress allowlist, secrets via proxy, warm pool dimensionné…)
**Risques résiduels non couverts par Kata** : (ex. secrets donnés au pod, egress, prompt injection)
```

Règle : la fiche AGT distingue toujours **ce que Kata apporte** (évasion vers le nœud, noyau partagé) de **ce qui relève d'autres contrôles** (egress, secrets, RBAC, audit). Cela évite de présenter Kata comme une protection contre la *prompt injection*.

## 7. Graphiques attendus (générés par `scripts/render-report.py`)

1. Boîtes à moustaches de la latence de démarrage (runc vs kata).
2. Barres groupées des débits (CPU, mémoire, disque, réseau) normalisés runc = 100.
3. Courbe densité : mémoire nœud consommée vs nombre de pods.
4. Courbe latence HTTP p99 vs charge (VU).
5. Matrice de chaleur des statuts FUN/SEC/DIND/AGT/VOL/SCR (VOL : une ligne par backend ; SCR : une ligne par fournisseur) (lignes = tests, colonnes = runtime).
6. Agents : barres empilées de la durée d'une tâche (temps LLM / temps outils / overhead sandbox), runc vs kata.
7. CI : barres empilées de la durée du pipeline par étape (checkout, compilation, tests, `docker build`, push), runc vs kata, par plateforme (Jenkins / GitHub).
8. Agents : latence de mise à disposition d'une sandbox (froid vs warm pool) et densité.

Conventions : runc et kata toujours dans les mêmes couleurs sur tous les graphiques, légende et unités sur chaque axe, mention « ENV-A indicatif » en filigrane le cas échéant.

## 8. Conventions de rédaction

- Langue : français ; termes techniques Kubernetes en anglais (`Pod`, `RuntimeClass`…).
- Chaque chiffre : unité, environnement, nombre de runs.
- Pas d'affirmation sans ID de test ou référence documentaire.
- Versions exactes (OCP, CRI-O, Kata/OSC, noyau hôte et invité, hyperviseur) dans l'annexe.
- Export : `pandoc report/rapport-comite.md -o report/rapport-comite.pdf` (ou `.docx` / `.html`).
