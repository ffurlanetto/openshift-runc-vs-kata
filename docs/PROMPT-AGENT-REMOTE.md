# Prompt : rejouer la campagne runc vs Kata sur un cluster distant

> À donner tel quel à l'agent interne. Remplacer les valeurs entre `<…>` avant envoi.
> L'agent travaille depuis un clone du dépôt `openshift-runc-vs-kata`, au commit indiqué ci-dessous.

---

Tu es chargé de rejouer, sur un cluster distant, la campagne de comparaison **runc vs Kata Containers** déjà exécutée sur OpenShift Local (ENV-A). Le banc, le plan de tests et le format de rapport sont dans ce dépôt. Ton travail : exécuter, vérifier, et rapporter des constats **précis et attribuables à une pile identifiée**.

## Contexte à lire d'abord

1. `README.md` : utilisation de `./precheck`, `./run`, `./setup`.
2. `02-PLAN-DE-TESTS.md` : catalogue des tests et attendus.
3. `RESULTATS-ENV-A.md` et `01-ENVIRONNEMENT.md` §3.4 : constats ENV-A et correctifs nécessaires.
4. `03-FORMAT-RAPPORT.md` : format des résultats et du rapport.

## Cible

| | |
|---|---|
| Contexte kube | `<nom du contexte>` (choisi au démarrage de `./precheck` / `./run`, ou `--context`) |
| Type | `<OpenShift + OSC>` ou `<Kubernetes + Kata>` |
| Identifiant | `ENV-B` (OpenShift x86_64 + OSC) ou `ENV-C` (Kubernetes) |
| Nœuds de bench | `<sélecteur, ex. kvr/bench=true>` : nœuds dédiés, jamais des nœuds de production |
| Site | `<connecté | airgappé (miroir Artifactory)>` |
| Commit du banc | `<sha>` |

## Règles impératives

- **Aucune action qui modifie les nœuds ou des composants partagés sans accord explicite écrit de l'opérateur** : installation ou mise à jour de Kata/OSC/Kyverno, `KataConfig`, MachineConfig, relabel SELinux, `kubectl debug node`, redémarrage, nettoyage disque. Si un prérequis manque : le signaler et proposer la commande, ne pas l'exécuter.
- `./setup` est réservé aux clusters de test dédiés. Il ne touche jamais un composant installé hors du banc ; ne pas contourner ce comportement.
- **Ne jamais modifier les ClusterPolicies Kyverno existantes.** Les policies du banc sont namespacées et créées dans les namespaces `kvr-*` uniquement.
- **Ne jamais utiliser `--allow-destructive`** (FUN-30 en pod réel peut rendre un nœud injoignable : constaté sur ENV-A).
- **Aucun secret** dans le dépôt, les résultats ou le rapport : kubeconfig, tokens, mots de passe, `dockerconfigjson`, URL internes non anonymisées. Relire `results/` et `evidence/` avant tout commit.
- Ne pas lancer de campagne sur un arbre git modifié (`--allow-dirty` interdit pour des résultats publiés).
- **Le dépôt est public** : tout ce qui est poussé (résultats, preuves, rapport, site GitHub Pages) est lisible par tous. Aucun nom d'hôte, IP, URL ou nom interne : anonymiser avant commit.
- **Tests à pod privilégié** : DIND-14, SCR-04, SCR-05 et VOL-12 lancent des pods privilégiés qui montent en lecture seule les disques du nœud ou le répertoire du kubelet (seuls les objets des pods de test sont lus, par UID ; aucune valeur de secret n'est écrite dans les preuves). Ne les lancer qu'avec l'**accord écrit** de l'exploitant du cluster ; sinon les exclure (`--skip` / sélection `--tests`) et le noter comme « non exécuté faute d'accord ».
- Si `./precheck` signale un bloquant, **s'arrêter et rapporter** : pas de contournement improvisé.

## Étapes

### 1. Poste et accès

```bash
git clone <url du dépôt> && cd openshift-runc-vs-kata && git checkout <sha>
# Site airgappé : index PyPI miroir, voir 01-ENVIRONNEMENT.md §2
export KVR_PYPI_INDEX=<url simple index Artifactory>     # seulement si airgappé
./precheck --context <ctx>
```

Prérequis du poste : `bash`, `git`, `kubectl` (±1 version mineure du serveur), `uv`. `helm` seulement si `./setup` est autorisé.

### 2. Profil du cluster dans `campaign.yaml`

Ajouter un profil, indexé par l'URL de l'API server (affichée par `./precheck`) :

```yaml
profiles:
  <https://api.cluster:6443>:
    env_id: ENV-B                       # ou ENV-C
    description: <texte sans nom interne>
    nested_virt: false                  # true seulement si les nœuds sont eux-mêmes des VM
    kata_runtime_class: kata            # RuntimeClass Kata principale (OSC : kata)
    node_selector: {kvr/bench: "true"}
```

Site airgappé : renseigner `registry.mirrors` (images **et** `oci://` des charts) et `registry.pull_secret`, puis vérifier avec `./run --print-images` que toutes les images listées existent sur le miroir. Le precheck fait un pull réel de chaque image.

Commiter le profil (sans secret) avant toute campagne.

### 3. Identifier précisément la pile — obligatoire avant toute conclusion

`./precheck` affiche la section **composants**, enregistrée aussi dans `campaign.json` (`fingerprint.components`) :

- distribution, version, Kubernetes, infrastructure ;
- CRI et version, OS et noyau des nœuds, CNI ;
- installation de Kata : **OSC** (`KataConfig`, version de l'opérateur, peer pods oui/non) ou **kata-deploy** (version, release Helm) ;
- pour chaque RuntimeClass Kata : handler, **shim (go / rust)**, hyperviseur, overhead.

Compléter à la main ce que le banc ne peut pas lire sans accès aux nœuds, **en citant la source** (sortie de commande, documentation, réponse Red Hat). Ne rien deviner : écrire « inconnu ».

| À relever | Comment |
|---|---|
| Version de Kata sous-jacente à OSC | Notes de version OSC, ou `kata-runtime --version` sur un nœud (avec accord) |
| Paramètres Kata effectifs : `default_memory`, `disable_guest_seccomp`, options `virtiofsd` (`--xattr`, `--sandbox`), `shared_fs` | Fichier de configuration Kata sur un nœud (avec accord), ou documentation OSC de la version |
| Noyau invité | Mesuré par SEC-01 (`proc_version.txt`) et par le smoke test du precheck |
| SELinux sur les nœuds | `getenforce` (avec accord) ; enforcing par défaut sur RHCOS |

Si le Kubernetes distant n'a **pas** de Kata : ne pas l'installer sans accord. Avec accord, `./setup kata --context <ctx>` installe kata-deploy (la distribution est détectée et passée en `k8sDistribution`). Sur des nœuds en SELinux enforcing hors OpenShift, les correctifs SELinux de `./setup` (réservés à OpenShift aujourd'hui) seront aussi nécessaires : le signaler.

### 4. Campagnes

Lister les RuntimeClass Kata du cluster et **faire une campagne par RuntimeClass Kata disponible**, plus runc :

```bash
./run --context <ctx> --env-id ENV-B --yes                                   # runc + RuntimeClass principale
./run --context <ctx> --env-id ENV-B --kata-runtime-class <autre> --runtimes kata --yes   # chaque autre RuntimeClass Kata
```

- Kyverno : POL est bloqué si Kyverno est absent. L'installer seulement avec accord (`./setup kyverno`), sinon `--skip POL` et le noter.
- AGT : les tests automatisés actuels (AGT-08/14/17/20) n'ont besoin ni de l'opérateur Agent Sandbox ni d'un LLM.
- DIND : variantes V1 à V5 (`V5` = Docker avec stockage en mémoire). Les tests Jenkins / GitHub Actions ne sont pas encore automatisés.
- VOL / SCR (tests automatisés : VOL-01, VOL-12, SCR-01 à SCR-05) : lancer d'abord un **essai** `./run --context <ctx> --phases VOL,SCR --runs 1 --no-warmup --yes` et classer les écarts (défaut du banc ou comportement), avant la campagne complète. VOL-01 utilise la StorageClass par défaut (backend `local`) ou `campaign.yaml › overrides.VOL-01.params.storage_class`. Les backends NFS, CIFS, S3, Vault et Conjur ne sont pas encore automatisés : ne rien installer pour eux.
- **Durées observées sur ENV-A (imbriqué)** : campagne complète runc + Kata ≈ 12 h (DIND en Kata ≈ 4 min par run) ; campagne Kata seule pour une 2e RuntimeClass ≈ 6 à 7 h. Sur bare metal, attendre nettement moins, mais prévoir une fenêtre longue. Lancer avec `nohup` (ou équivalent) pour survivre à la fin de session : `nohup ./run … --yes </dev/null > run.log 2>&1 &`.
- Rejeu à l'identique d'une campagne : `./run --replay results/<campagne>/campaign.json` (avec `--strict` pour refuser tout écart de code ou d'environnement).
- Surveiller : disque des nœuds (le precheck alerte au-delà de 70 %), namespaces `kvr-*` résiduels (`./run --cleanup`).

### 5. Vérification des résultats

```bash
uv run scripts/validate_results.py
uv run scripts/report.py --campaign <campagne runc+kata> --campaign <campagne autre RuntimeClass> --site docs-env-b
```

`report.py` produit `report/donnees.md` (fiches par test, une colonne par runtime, médiane, p5–p95, n, verdict de significativité) et un site statique. Sur la branche `env-b`, générer le site dans `docs-env-b/` pour ne pas écraser le site ENV-A de `main`.

Pour chaque statut `FAIL`, `PARTIAL`, `NOT_SUPPORTED` ou `BLOCKED` :
1. lire `results/…/run-<n>.json` (observations, métriques) et `evidence/…` (manifestes, `events.txt`, `pods.json`, sorties, `traceback.txt`) ;
2. **classer la cause** dans une seule de ces catégories :
   - **défaut du banc** (test mal écrit, critère inadapté) : corriger dans une branche, faire relire, rejouer ;
   - **configuration du cluster** (SCC, policy existante, quota, image absente du miroir) ;
   - **limite du runtime** (comportement de Kata, ou de runc, reproduit et expliqué) ;
   - **cause inconnue** : le dire, avec ce qui a été essayé.
3. Une limite du runtime n'est retenue qu'avec une **preuve reproduite** (au moins 2 runs) et un **mécanisme identifié** (message d'erreur, paramètre de configuration, documentation). Sinon, la classer « à confirmer ».

### 6. Constats ENV-A à confirmer ou infirmer explicitement

Pour chacun : résultat sur ta cible, pile exacte, preuve, et si l'écart avec ENV-A s'explique (runtime Go vs Rust, OSC vs kata-deploy, virtualisation imbriquée, configuration).

| # | Constat ENV-A (Kata 4.4 kata-deploy, runtime Rust, CRC arm64 imbriqué) | Hypothèse à tester |
|---|---|---|
| 1 | Pod Kata en `hostNetwork` : nœud injoignable | Ne pas reproduire en réel. Vérifier seulement qu'il est **admis** (FUN-30, dry-run) et que POL-18 le bloque |
| 2 | Mémoire de la VM = limite mémoire du pod ; à 64Mi la VM ne démarre pas | Runtime Go/OSC : mémoire de base (`default_memory`) + limite → probablement non reproduit |
| 3 | Seccomp `RuntimeDefault` non appliqué dans la VM (POL-17) | Dépend de `disable_guest_seccomp` |
| 4 | `ephemeral-storage` dépassé sans éviction (POL-16) | À confirmer ; mécanisme non encore expliqué |
| 5 | OOM remonté `Error` au lieu de `OOMKilled` (FUN-17) | Dépend du shim |
| 6 | File capabilities perdues (xattr non transmis par virtio-fs) : buildah/BuildKit rootless KO (DIND-01/05, V2–V4) | Dépend de `virtiofsd --xattr` |
| 7 | Docker overlay sur `emptyDir` virtio-fs : build KO (DIND-05 V1) ; OK avec stockage en mémoire (V5) | Probablement reproduit (propre à virtio-fs) ; tester aussi un PVC en mode bloc si une StorageClass le permet |
| 8 | `/dev/fuse` (annotation CRI-O) non fourni dans la VM : buildah sans privilège KO (V3) | À vérifier |
| 9 | Kyverno : comportement identique runc / Kata, aucun contournement | Devrait être reproduit |
| 10 | Pod Ready : 0,9 s runc vs 19,4 s Kata (imbriqué) | Chiffres ENV-B attendus très inférieurs : ce sont **ceux-là** qui vont au comité |
| 11 | AGT-17 multiplication de processus : runc contenu par la **limite mémoire** (conteneur OOMKilled en ≈ 2 s, `pids.max=max` dans le conteneur) ; Kata (Rust) contenu par une **limite pids dans l'invité** (`pids.max=336`) | Relever `pids.max` vu dans le conteneur pour chaque runtime ; origine du 336 à identifier |
| 12 | Démarrage de VM intermittent : agent injoignable en 60 s (`vsock … ETIMEDOUT`) sous charge | Attendu propre à l'imbriqué : confirmer l'absence sur bare metal |
| 13 | SCR-04 : un administrateur du nœud lit les secrets d'un pod Kata (tmpfs kubelet, environnement, mémoire de la VM) | Attendu identique : Kata ne protège pas du nœud (seule CoCo le fait). Si non exécuté faute d'accord, le dire |
| 14 | SCR-05 / VOL-12 : un pod compromis avec un `hostPath` ou des disques bloc atteint-il les secrets / volumes d'autres pods ? | À mesurer : ENV-A en cours au moment de la rédaction de ce prompt ; voir `RESULTATS-ENV-A.md` à jour |

## Livrables

1. Les campagnes commitées (`results/`, `evidence/` anonymisés) et le profil dans `campaign.yaml`, sur une branche `env-b` (ou `env-c`), via une pull request.
2. `RESULTATS-ENV-B.md` (ou `ENV-C`) sur le modèle de `RESULTATS-ENV-A.md`, avec en tête la **pile exacte** (section 3) et pour chaque constat : statut, preuve (chemin du fichier), catégorie de cause, niveau de confiance (vérifié / à confirmer).
3. Le tableau de la section 6 rempli.
4. Le site généré (`docs-env-b/`) : ne **pas** activer GitHub Pages depuis la branche sans accord ; le site de `main` sera fusionné après relecture.
5. La liste des actions refusées faute d'accord, des tests `BLOCKED` et de leur prérequis manquant.

## Style des conclusions

- Toujours préciser **quelle pile** : « Kata 3.x via OSC 1.y, runtime Go, QEMU RHEL, x86_64 bare metal » et pas « Kata ».
- Distinguer **mesuré** (chiffre, fichier de preuve) et **déduit** (raisonnement), et dire lequel.
- Ne pas généraliser un constat d'un runtime ou d'un environnement à un autre sans l'avoir mesuré.
- Une métrique de performance s'accompagne de n, de la médiane et de la dispersion, et de la mention « imbriqué » le cas échéant.
- En cas de doute, écrire « non déterminé » et ce qu'il faudrait pour trancher.
