# 02 — Plan de tests : pods runc vs Kata Containers sur OpenShift

| | |
|---|---|
| Version | 0.2 (brouillon pour revue) |
| Date | 2026-11-23 |
| Périmètre | OpenShift 4.22, runtime par défaut CRI-O/runc vs Kata Containers (OpenShift Sandboxed Containers ou kata-deploy upstream) |
| Livrable final | Rapport comité au format défini dans `03-FORMAT-RAPPORT.md` |

## 1. Objectifs

1. **Valider** que les workloads cibles fonctionnent avec Kata sans modification (ou identifier les modifications nécessaires).
2. **Mesurer** le coût de Kata (latence de démarrage, overhead mémoire/CPU, I/O, réseau, densité).
3. **Démontrer** le gain d'isolation de Kata (surface d'attaque noyau, évasion de conteneur, pods privilégiés, voisins bruyants).
4. **Évaluer** l'exploitabilité (installation, mise à jour, observabilité, debug, support).
5. **Produire** une matrice avantages / inconvénients / limites et une recommandation d'usage (quels workloads sur quel runtime).
6. **Valider deux cas d'usage cibles**, chacun sous les angles fonctionnel, performance et sécurité :
   - **CI dans Kata (DIND)** : exécuter les pipelines Jenkins et GitHub Actions (compilation, tests, packaging, `docker build` sur Dockerfile, tests avec conteneurs) dans des pods Kata, sans que le pod privilégié requis menace le nœud.
   - **Agents IA autonomes (AGT)** : exécuter des agents qui lancent du code non relu (shell, Python, installation de paquets, navigateur) dans des sandboxes isolées, à l'échelle.

Hors périmètre : Confidential Containers (CoCo / TEE), peer-pods (Kata en VM cloud), gVisor. Ils peuvent faire l'objet d'une seconde phase.

## 2. Rappel des deux modèles

| | runc (défaut) | Kata Containers |
|---|---|---|
| Isolation | Namespaces + cgroups + SELinux + seccomp, **noyau de l'hôte partagé** | Chaque pod dans une **micro-VM** (QEMU/KVM ou Cloud Hypervisor) avec son propre noyau invité |
| Frontière de sécurité | Noyau Linux de l'hôte | Hyperviseur (KVM) + noyau invité + SELinux `container_kvm_t` sur le processus VMM |
| Sélection | Par défaut | `spec.runtimeClassName: kata` (RuntimeClass, handler CRI-O `kata`) |
| Overhead déclaré | Aucun | `RuntimeClass.overhead.podFixed` (OSC : ~350 Mi mémoire, 250 m CPU) |
| Prérequis nœud | Aucun | Virtualisation matérielle (`/dev/kvm`) : bare metal ou nested |

## 3. Environnements

| ID | Description | Usage | Statut |
|---|---|---|---|
| **ENV-A** | CRC 4.22.1 arm64 (Mac M5 Max), vfkit `--nested`, Kata via `kata-deploy` upstream, 12 vCPU / 24 Go | Fonctionnel (FUN), sécurité (SEC), découverte des limites (LIM), perf **indicative** | À préparer (cf. `01-ENVIRONNEMENT.md` §3) |
| **ENV-B** | OCP 4.22 x86_64 bare metal (≥ 1 nœud worker metal), OSC 1.13 + `KataConfig` | Perf de référence (PERF), densité, exploitation (OPS), validation finale | À provisionner |

Chaque résultat indique l'environnement. **Un chiffre de performance issu d'ENV-A n'est jamais comparé à un chiffre d'ENV-B.**

## 4. Méthodologie

### 4.1 Principe de comparaison A/B
- Chaque test est exécuté **deux fois avec le même manifeste**, seule la ligne `runtimeClassName` change (`runc` = champ absent, `kata` = `runtimeClassName: kata`).
- Même image, même nœud, mêmes `requests/limits`, même namespace (ou deux namespaces jumeaux `bench-runc` / `bench-kata`).
- Les manifestes sont générés depuis un template unique (`tests/<ID>/pod.tmpl.yaml`) pour garantir l'équivalence.

### 4.2 Rigueur des mesures
- **Répétitions** : ≥ 5 runs par mesure de perf (≥ 30 pour la latence de démarrage), on rapporte médiane, p95, min, max, écart-type.
- **Warm-up** : 1 run écarté. Images pré-tirées sur le nœud (`imagePullPolicy: IfNotPresent` + pré-pull) pour ne pas mesurer le pull.
- **Bruit** : nœud dédié (taint/label `bench=true` sur ENV-B), podman machine et autres charges arrêtées sur ENV-A, alternance runc/kata (ABAB) pour neutraliser la dérive thermique.
- **Écart significatif** : on qualifie une différence de « significative » si l'écart des médianes dépasse 5 % **et** que les intervalles [p5 ; p95] ne se recouvrent pas.
- **Traçabilité** : chaque run produit un fichier `results/<campagne>/<ENV>/<ID>/<runtime>/run-<n>.json` (schéma dans `03-FORMAT-RAPPORT.md`).

### 4.3 Statuts possibles d'un test
`PASS` · `FAIL` · `PARTIAL` (fonctionne avec contournement) · `NOT_SUPPORTED` (limite connue du runtime) · `BLOCKED` (environnement) · `N/A`

### 4.4 Outillage
- Image d'outillage `kata-bench` (UBI 9 + fio, iperf3, sysbench, stress-ng, netperf, redis, postgresql, amicontained, cdk, deepce), multi-arch amd64/arm64, construite avec podman.
- Charge HTTP : `k6` / `hey` depuis le poste ou depuis un pod runc « client » fixe.
- Collecte : `oc get pod -o json` (timestamps des conditions), Prometheus (`container_*`, `kata_*` via kata-monitor), `crictl stats` et `ps`/`smem` sur le nœud via `oc debug node`.
- Sécurité : `kube-bench`, `kubescape`, `trivy`, `compliance-operator`, Kyverno, scénarios d'évasion manuels.
- **Automatisation** : `./precheck` et `./run` (voir README). Prérequis poste : `kubectl`, `uv`, `git` ; `helm` pour `./setup`.

## 5. Phase 0 — Préparation (PREP)

| ID | Action | Critère de sortie |
|---|---|---|
| PREP-01 | `./precheck` sans bloquant sur la cible | Code retour 0 |
| PREP-02 | `/dev/kvm` présent sur le(s) nœud(s) | `test -c /dev/kvm` |
| PREP-03 | Installation Kata (ENV-A : `helm install kata-deploy` ; ENV-B : operator OSC + `KataConfig`) | RuntimeClass `kata` présente, nœud `Ready`, temps d'installation et nb de reboots notés |
| PREP-04 | Smoke test : pod `runtimeClassName: kata`, `uname -r` ≠ noyau hôte | Noyau invité visible |
| PREP-05 | Image `kata-bench` construite et disponible pour le cluster | Pull OK en runc et kata |
| PREP-06 | Monitoring activé, kata-monitor scrappé | Métriques `kata_*` dans Prometheus |
| PREP-07 | Namespaces `bench-runc` / `bench-kata`, SCC et quotas identiques | `oc diff` vide hormis le runtime |
| PREP-08 | Images de build disponibles en amd64/arm64 : `docker:dind`, `docker:dind-rootless`, `quay.io/buildah/stable`, `moby/buildkit:rootless`, `jenkins/inbound-agent`, `ghcr.io/actions/actions-runner` | Pull OK |
| PREP-08b | CI : controller Jenkins (Helm, plugin Kubernetes) et ARC (controller + runner scale set, GitHub App ou PAT) installés ; projets de référence P-JAVA / P-NODE disponibles ; registre de destination accessible | Un pipeline trivial passe en runc |
| PREP-09 | Agent Sandbox installé (ENV-A : manifests upstream `kubernetes-sigs/agent-sandbox` ; ENV-B : `agent-sandbox-operator` Red Hat, canal *preview*), `SandboxTemplate` runc et kata | `Sandbox` `Ready` dans les deux runtimes |
| PREP-10 | Backend LLM pour les agents : API distante (ex. Claude API) via proxy d'egress, **ou** modèle local (Ollama/llama.cpp sur le Mac, joignable via `host.crc.testing`) | Appel de complétion OK depuis un pod |
| PREP-12 | Kyverno présent (existant sur le cluster, ou `./setup kyverno` sur un cluster de test) | Détecté par `./precheck --phases POL` |
| PREP-13 | Site airgappé : images et charts disponibles dans le miroir (`./run --print-images`), règles de réécriture et secret de pull dans `campaign.yaml`, index PyPI miroir (`KVR_PYPI_INDEX`) | Contrôle « images » du precheck OK |
| PREP-11 | Harnais « agent rejoué » : script déterministe qui rejoue une séquence d'appels d'outils (y compris malveillants) sans LLM, pour des tests de sécurité reproductibles | Séquence de référence exécutée en runc et kata |
| PREP-14 | Backends de stockage (VOL) déclarés dans `campaign.yaml` (`backends.storage`) : StorageClass local, NFS, CIFS, S3 CSI ; endpoint et bucket S3 ; identifiants par **référence** à des Secrets existants. ENV-A : serveurs NFS, Samba et MinIO + drivers CSI déployés par `./setup storage` (cluster de test seulement) | `./precheck --phases VOL` : chaque backend monté par un pod de test |
| PREP-15 | Fournisseurs de secrets (SCR) déclarés dans `campaign.yaml` (`backends.secrets`) : Vault (adresse, CA, méthode d'auth, rôle, chemin de test), Conjur (URL, compte, authentificateur, *host*), Secrets Store CSI Driver, injector et opérateurs présents. ENV-A : Vault dev et Conjur OSS par `./setup secrets` | `./precheck --phases SCR` : lecture d'un secret de test par fournisseur |

## 6. Catalogue de tests

Colonne **Env** : A = ENV-A suffit, B = ENV-B requis, A/B = indicatif sur A, référence sur B.
Colonne **Prio** : P1 = obligatoire pour la décision, P2 = important, P3 = si le temps le permet.

### 6.1 Fonctionnel (FUN) — « est-ce que ça marche pareil ? »

| ID | Test | Attendu | Env | Prio |
|---|---|---|---|---|
| FUN-01 | Pod simple, Deployment, ReplicaSet, scaling 0→N→0 | Identique | A | P1 |
| FUN-02 | StatefulSet avec PVC RWO (Filesystem) | Identique | A | P1 |
| FUN-03 | PVC `volumeMode: Block` | À vérifier (device passthrough dans la VM) | A | P2 |
| FUN-04 | ConfigMap / Secret montés en volume + **mise à jour à chaud** propagée | À vérifier (propagation via virtio-fs) | A | P1 |
| FUN-05 | `emptyDir` disque et `emptyDir` `medium: Memory` (+ `sizeLimit`) | À vérifier (le tmpfs consomme la RAM de la VM) | A | P1 |
| FUN-06 | Volume `hostPath` | À vérifier, limite attendue | A | P2 |
| FUN-07 | Downward API, projected volumes, ServiceAccount token | Identique | A | P2 |
| FUN-08 | Init containers, sidecars natifs (`restartPolicy: Always`) | Identique | A | P1 |
| FUN-09 | Probes liveness / readiness / startup (exec, http, tcp, grpc) | Identique | A | P1 |
| FUN-10 | `oc exec`, `oc logs -f`, `oc cp`, `oc port-forward`, `oc attach` | Identique | A | P1 |
| FUN-11 | `oc debug pod/…` et **ephemeral containers** | Limite attendue côté Kata | A | P1 |
| FUN-12 | Service ClusterIP, NodePort, Route (edge/passthrough/reencrypt), DNS | Identique | A | P1 |
| FUN-13 | NetworkPolicy (deny-all, allow ciblé) appliquée au pod Kata | Identique | A | P1 |
| FUN-14 | Multus : interface secondaire (macvlan/bridge) | À vérifier | A/B | P3 |
| FUN-15 | Job, CronJob, `activeDeadlineSeconds`, `backoffLimit` | Identique | A | P2 |
| FUN-16 | Arrêt gracieux : SIGTERM, `preStop`, `terminationGracePeriodSeconds` | Identique, mesurer le délai | A | P1 |
| FUN-17 | OOM : dépassement de `limits.memory` | Conteneur `OOMKilled` (et non la VM entière), raison correctement remontée | A | P1 |
| FUN-18 | Limites CPU (throttling) et `requests` : respect effectif | À mesurer (vCPU de la VM vs quota cgroup) | A/B | P1 |
| FUN-19 | HPA (CPU / mémoire) sur Deployment Kata | Métriques remontées, scaling OK | A | P2 |
| FUN-20 | In-place pod resize (`resize` subresource) | À vérifier (hotplug CPU/mémoire) | A | P3 |
| FUN-21 | Sysctls (safe et unsafe) | Avec Kata, les sysctls s'appliquent au noyau invité | A | P2 |
| FUN-22 | Pod privilégié / capabilities ajoutées (`NET_ADMIN`, `SYS_ADMIN`) | Effet limité à la VM | A | P2 |
| FUN-23 | Build in-cluster : BuildConfig / buildah / Tekton task dans un pod Kata | Kata permet des builds plus isolés, à vérifier | A | P2 |
| FUN-24 | Images variées : UBI, UBI-minimal, distroless, Alpine (musl), image root vs non-root, `runAsUser` arbitraire (SCC `restricted-v2`) | Identique | A | P1 |
| FUN-25 | Workloads de référence de l'entreprise (2 à 3 applis réelles : web, base de données, batch) | Identique, à confirmer | A/B | P1 |
| FUN-26 | Redémarrage du nœud, redémarrage de CRI-O | Pods Kata recréés proprement | A/B | P2 |
| FUN-27 | Drain / cordon / PodDisruptionBudget, reschedule sur un autre nœud | Identique | B | P2 |
| FUN-28 | GPU / device plugin (si cas d'usage) | Limite attendue, nécessite configuration spécifique | B | P3 |
| FUN-29 | Horloge / timezone / NTP dans le pod (dérive de l'horloge invitée) | Pas de dérive significative | A | P3 |
| FUN-30 | `hostNetwork`, `hostPID`, `hostIPC` | Non supporté avec Kata. **Constat ENV-A : le pod Kata en hostNetwork a rendu le nœud injoignable.** Par défaut, Kata n'est vérifié que par dry-run d'admission ; pod réel seulement avec `--allow-destructive` (cluster jetable) | A | P1 |

### 6.2 Performance (PERF) — « combien ça coûte ? »

| ID | Mesure | Outil / méthode | Métriques | Env | Prio |
|---|---|---|---|---|---|
| PERF-01 | Latence de démarrage d'un pod (création → `Ready`) | Script de création, timestamps `PodScheduled`→`ContainersReady` | ms : médiane, p95 (n=30) | A/B | P1 |
| PERF-02 | Démarrage en rafale : 10 / 50 / 100 pods simultanés | Deployment `replicas=N` | Temps jusqu'au dernier `Ready`, erreurs | B | P1 |
| PERF-03 | Durée de suppression d'un pod | `oc delete` horodaté | ms | A/B | P2 |
| PERF-04 | Overhead mémoire par pod (pod « pause » / sleep) | RSS du VMM + virtiofsd + shim sur le nœud vs RSS conteneur runc | Mi par pod | A/B | P1 |
| PERF-05 | Densité maximale par nœud (mémoire fixe) | Montée en charge jusqu'à refus de scheduling / OOM | Nb de pods, comportement en saturation | B | P1 |
| PERF-06 | CPU calcul pur | `sysbench cpu`, `stress-ng --cpu` | events/s, bogo-ops/s | A/B | P1 |
| PERF-07 | Bande passante mémoire / latence | `sysbench memory`, `stress-ng --stream` | MiB/s | A/B | P2 |
| PERF-08 | Coût des appels système | `stress-ng --syscall`, `--getpid`, `--fork` | ops/s | A/B | P2 |
| PERF-09 | I/O disque : rootfs du conteneur | `fio` randread/randwrite 4k, seq 1M | IOPS, MB/s, latence p99 | A/B | P1 |
| PERF-10 | I/O disque : `emptyDir` et PVC | `fio` idem | idem | A/B | P1 |
| PERF-11 | Réseau pod↔pod même nœud | `iperf3` TCP/UDP, `netperf TCP_RR` | Gbit/s, transactions/s, latence | A/B | P1 |
| PERF-12 | Réseau pod↔pod inter-nœuds, via Service | `iperf3` | Gbit/s | B | P2 |
| PERF-13 | Latence applicative HTTP (nginx / appli de réf.) | `k6` palier 10→500 VU | RPS, latence p50/p95/p99, erreurs | A/B | P1 |
| PERF-14 | Base de données | `pgbench` (PostgreSQL), `redis-benchmark` | TPS, latence | A/B | P2 |
| PERF-15 | Overhead CPU hôte au repos (pods idle) | CPU nœud avec 20 pods idle | m CPU / pod | B | P2 |
| PERF-16 | Voisin bruyant : 1 pod victime + 1 pod `stress-ng` agressif (CPU, mémoire, I/O) | Dégradation de la victime | % de dégradation | B | P2 |

### 6.3 Sécurité (SEC) — « qu'est-ce que Kata apporte vraiment ? »

Tous les scénarios sont exécutés **uniquement sur les environnements de test**, dans le cadre de cette campagne.

Principes de protection contre l'évasion couverts : noyau dédié (SEC-01), visibilité du nœud (SEC-03), évasion d'un pod privilégié (SEC-04), `hostPath` (SEC-05), surface noyau (SEC-08), modification du noyau du nœud (SEC-09), ressources (SEC-10, AGT-17), isolation entre pods (SEC-18), escalade de privilèges (SEC-19), lecture par l'administrateur du nœud (SCR-04). Les tests qui réalisent une évasion réelle ou lisent le nœud (SEC-04, 05, 09, et le volet nœud de SEC-18) ne s'exécutent qu'avec `./run --non-safe`. Les canaux auxiliaires (Spectre et apparentés) sont hors périmètre.

| ID | Scénario | Attendu runc | Attendu Kata | Env | Prio |
|---|---|---|---|---|---|
| SEC-01 | Identification du noyau : `uname -a`, `/proc/version`, `dmesg` | Noyau de l'hôte | Noyau invité dédié | A | P1 |
| SEC-02 | Inventaire de l'isolation : `amicontained` (namespaces, caps, seccomp, AppArmor/SELinux) | Profil restreint | Profil + frontière VM | A | P1 |
| SEC-03 | Visibilité de l'hôte : processus, montages, périphériques (`/proc`, `/sys`, `/dev`), interfaces réseau | Partiellement masqué | Seulement la VM | A | P1 |
| SEC-04 | Pod **privilégié** (SCC `privileged`) : accès aux disques hôte (`/dev/sda`, `/dev/vda`), `nsenter -t 1`, montage du FS hôte | **Compromission de l'hôte** | Confiné à la VM | A | P1 |
| SEC-05 | `hostPath: /` monté en écriture | Accès complet à l'hôte | À mesurer (partage virtio-fs : accès toujours possible → limite à documenter) | A | P1 |
| SEC-06 | Toolkit d'évasion automatisé (`cdk evaluate`, `deepce`) en pod restreint puis privilégié | Liste des vecteurs exploitables | Liste des vecteurs exploitables | A | P1 |
| SEC-07 | Classe de vulnérabilités « runtime » (type CVE-2019-5736, CVE-2024-21626 « Leaky Vessels ») : vérifier si le binaire runtime / les fd de l'hôte sont atteignables depuis le pod. **Pas d'exploit réel**, uniquement l'analyse de la surface | Surface présente | Surface déplacée dans la VM | A | P2 |
| SEC-08 | Classe « exploit noyau » : appels système rares/dangereux (`unshare`, `keyctl`, `bpf`, `userfaultfd`, `io_uring`) acceptés ou refusés | Noyau hôte exposé (filtré par seccomp) | Noyau invité exposé ; l'hôte ne voit que les appels du VMM | A | P1 |
| SEC-09 | Sysctl unsafe / chargement de module noyau (`modprobe`, `insmod`) depuis un pod privilégié | Impacte l'hôte | Impacte la VM seulement | A | P2 |
| SEC-10 | Isolation des ressources : fork bomb, épuisement mémoire, remplissage disque `emptyDir` | Contenu par cgroups/pids-limit | Contenu par la VM + cgroups du sandbox | A/B | P1 |
| SEC-11 | Confinement SELinux du VMM sur l'hôte (`ps -Z` : `container_kvm_t`) et du conteneur runc (`container_t`, MCS) | `container_t` | `container_kvm_t` | A/B | P2 |
| SEC-12 | Secrets : un pod Kata voit-il les secrets/volumes d'un autre pod ? Accès au token SA, au metadata service | Isolé | Isolé | A | P2 |
| SEC-13 | Réseau : NetworkPolicy contournable depuis un pod privilégié ? (manipulation iptables, ARP spoofing) | Possible en privilégié + hostNetwork | Confiné à la VM | A | P2 |
| SEC-14 | **Détection runtime** : Falco / RHACS / auditd détectent-ils un `exec` shell, une écriture dans `/etc`, une connexion sortante ? | Détecté (eBPF sur l'hôte) | **Risque d'angle mort** : les syscalls internes à la VM ne sont pas vus par l'hôte | B | P1 |
| SEC-15 | Conformité : `compliance-operator` (profil CIS OCP), `kube-bench`, `kubescape` avant / après installation Kata | Baseline | Pas de régression | A/B | P2 |
| SEC-16 | Scan des composants ajoutés (images operator / kata-deploy, QEMU, noyau invité) : `trivy`, CVE connues, fréquence de patch | — | Nouvelle surface à maintenir | A | P2 |
| SEC-17 | Revue du modèle de menace : qui peut choisir `runtimeClassName` ? Imposer Kata par namespace (admission policy / Kyverno / ValidatingAdmissionPolicy) | — | Politique d'imposition testée | A | P1 |
| SEC-18 | **Isolation entre pods** : une victime porte des marqueurs (processus, mémoire, fichier, paquet réseau). Observateurs : voisin runc, voisin du même runtime, et (mode non sûr) administrateur du nœud (`hostPID`, `hostNetwork`, racine en lecture) | Voisins : rien. Nœud : tout | Voisins : rien. Nœud : processus invisible (seul QEMU), mais **mémoire, fichiers, réseau atteignables** (Kata ne protège pas le pod du nœud ; rôle de CoCo) | A/B | P1 |
| SEC-19 | **Escalade de privilèges dans le pod** : `no_new_privs`, capacités effectives, binaire setuid-root lancé par un non-root avec `allowPrivilegeEscalation` false / true, capacités utilisables en root, user namespaces | Garde-fous appliqués | Identiques à runc (root du pod = root de la VM, pas du nœud) | A/B | P1 |

### 6.4 Exploitation (OPS) — « peut-on le faire tourner au quotidien ? »

| ID | Sujet | Mesure / critère | Env | Prio |
|---|---|---|---|---|
| OPS-01 | Installation : étapes, durée, reboots de nœud (MachineConfig) | Durée, nb de reboots, automatisable GitOps ? | A/B | P1 |
| OPS-02 | Mise à jour OCP avec Kata installé, mise à jour de l'operator OSC | Impact sur les pods Kata, durée | B | P1 |
| OPS-03 | Désinstallation propre | Nœuds revenus à l'état initial | A/B | P2 |
| OPS-04 | Observabilité : métriques pod/conteneur dans la console, Prometheus, kata-monitor, dashboards | Métriques manquantes listées | A/B | P1 |
| OPS-05 | Logs : collecte cluster-logging / Vector pour les pods Kata | Identique ? | A/B | P2 |
| OPS-06 | Debug : `oc debug`, `crictl`, accès console de la VM, `must-gather` OSC | Procédure documentée | A/B | P1 |
| OPS-07 | Capacity planning : prise en compte de `overhead.podFixed` par le scheduler et les quotas | Quotas consommés = requests + overhead | A | P1 |
| OPS-08 | Hétérogénéité des nœuds : nœuds sans KVM, `scheduling.nodeSelector` de la RuntimeClass | Pods Kata jamais schedulés sur un nœud non compatible | B | P2 |
| OPS-09 | Support et cycle de vie : matrice de support Red Hat, architectures, versions, licences | Synthèse documentaire | — | P1 |
| OPS-10 | Coût : surconsommation de ressources (PERF-04/05) traduite en nœuds supplémentaires | € / an estimé | B | P2 |

### 6.8 Policies d'admission Kyverno (POL)

**Enjeu** : les bonnes pratiques (non-root, requests/limits, pas de privilège, pas d'accès à l'hôte, images épinglées) sont normalement imposées par des policies d'admission. Il faut vérifier trois choses :
- qu'elles s'appliquent **de la même façon** aux pods runc et Kata ;
- qu'on peut s'en servir pour **forcer** Kata (mutation + validation) ;
- si un pod peut **dépasser à l'exécution** ce que l'admission a validé (limites CPU, stockage, privilèges effectifs).

**Mise en œuvre** :
- Kyverno détecté automatiquement. Sur un cluster distant, **l'installation existante est utilisée telle quelle**.
- Les policies du banc sont **namespacées** dans les namespaces de test, donc aucune modification des ClusterPolicies du cluster.
- Catalogue unique `policies/kyverno/catalog.yaml`, rendu selon la version de Kyverno :
  - `NamespacedValidatingPolicy` / `NamespacedMutatingPolicy` (CEL, Kyverno ≥ 1.14 environ) ;
  - sinon `kyverno.io/v1 Policy` + `validate.cel`.
- Tests d'admission par **création à blanc côté serveur** (`--dry-run=server`), qui traverse toute la chaîne d'admission sans créer de pod.

| ID | Aspect | Test | Attendu runc | Attendu Kata | Env | Prio |
|---|---|---|---|---|---|---|
| POL-01 | SEC | Non-root obligatoire : pod conforme admis, pod root refusé, Deployment root refusé (autogen) | PASS | PASS | A | P1 |
| POL-02 | SEC | Requests CPU/mémoire et limite mémoire obligatoires | PASS | PASS | A | P1 |
| POL-03 | SEC | Plafond des limits (mémoire, CPU) | PASS | PASS | A | P2 |
| POL-04 | SEC | Conteneurs privilégiés interdits | PASS | PASS | A | P1 |
| POL-05 | SEC | Escalade de privilèges interdite | PASS | PASS | A | P1 |
| POL-06 | SEC | Capabilities restreintes (drop ALL, ajout NET_BIND_SERVICE seulement) | PASS | PASS | A | P1 |
| POL-07 | SEC | hostNetwork / hostPID / hostIPC interdits | PASS | PASS | A | P1 |
| POL-08 | SEC | hostPath interdit | PASS | PASS | A | P1 |
| POL-09 | SEC | seccomp RuntimeDefault/Localhost obligatoire | PASS | PASS | A | P2 |
| POL-10 | SEC | Images par digest obligatoires | PASS | PASS | A | P2 |
| POL-11 | SEC | **Pod privilégié autorisé seulement avec Kata** (cas CI/DIND) | Privilégié refusé | Privilégié admis | A | P1 |
| POL-12 | SEC | **Forcer Kata** : mutation qui ajoute `runtimeClassName`, validation qui refuse tout autre runtime ; l'**overhead** de la RuntimeClass est-il appliqué après mutation ? | Muté vers Kata | Inchangé | A | P1 |
| POL-13 | SEC | Mode **Audit** : pod non conforme admis, avertissement client, entrée dans le PolicyReport (délai mesuré) | PASS | PASS | A | P1 |
| POL-14 | SEC | **Contournements** en Enforce : Job, CronJob, conteneur éphémère privilégié (`kubectl debug --profile=sysadmin`) | Tous refusés | Tous refusés | A | P1 |
| POL-15 | FUN | **Dépassement CPU à l'exécution** : 4 threads actifs sous une limite de 500m, consommation réelle mesurée | ≤ limite | ≤ limite ? (cgroup de la VM, vCPU) | A/B | P1 |
| POL-16 | FUN | **Dépassement ephemeral-storage** : écriture de 300 Mi sous une limite de 100 Mi, éviction attendue | Évincé | Évincé ? (écritures via la VM) | A | P1 |
| POL-17 | SEC | **Privilèges effectifs** d'un pod conforme : UID ≠ 0, NoNewPrivs, CapEff = 0, seccomp actif, /etc en lecture seule | PASS | PASS (appliqués par l'agent Kata) | A | P1 |
| POL-18 | SEC | **Garde-fou hostNetwork** (issu de FUN-30) : policy `disallow-hostnetwork-kata` ; un pod `hostNetwork` reste admis en runc, est refusé avec une RuntimeClass Kata (dry-run uniquement) | Admis | Refusé | A | P1 |

Le dépassement de la limite mémoire est couvert par FUN-17.

### 6.5 Limites (LIM) — inventaire consolidé

Section alimentée par les statuts `NOT_SUPPORTED` / `PARTIAL` des catégories précédentes, à vérifier spécifiquement :
`hostNetwork`, `hostPID/IPC`, ephemeral containers, `hostPath` et sous-chemins, volumes Block, devices/GPU, in-place resize, métriques cAdvisor par conteneur, profils seccomp/SELinux personnalisés appliqués à l'intérieur de la VM, `procMount: Unmasked`, user namespaces (`hostUsers: false`), checkpoint/restore, live migration, prise en charge arm64, pilote de stockage Docker (overlay2) sur virtio-fs, MTU des réseaux imbriqués, virtualisation imbriquée dans la VM Kata (micro-VM d'agent dans Kata), suspension/reprise de sandbox.

### 6.6 CI dans Kata : Jenkins / GitHub Actions avec Docker (DIND)

**Enjeu** : faire tourner les pipelines CI (Jenkins et GitHub Actions) dans des pods Kata. Ces pipelines **compilent, testent et packagent** du code, y compris une **étape `docker build` sur un Dockerfile**. Ils lancent aussi souvent des conteneurs pendant les tests (Testcontainers, services). Avec runc, il faut un pod **privilégié**, donc un accès root au nœud, et ce pour du code venant potentiellement de n'importe quelle PR. Avec Kata, le privilège reste confiné à la VM du job.

**Architecture testée**

| Plateforme | Mise en œuvre | Point d'injection de Kata |
|---|---|---|
| **Jenkins** | Controller Jenkins (chart Helm officiel, sur runc) + plugin **Kubernetes** : un pod agent éphémère par build (`jnlp` + conteneurs d'outils + sidecar `docker:dind`) | `runtimeClassName: kata` dans le `podTemplate` |
| **GitHub Actions** | **Actions Runner Controller (ARC)**, *runner scale sets* éphémères, un runner = un job | `runtimeClassName: kata` dans le template du runner. Deux modes : `containerMode: dind` (prioritaire) et `containerMode: kubernetes` (les pods de job créés par les container hooks doivent aussi être en Kata) |

**Variantes du moteur de build** (pour chaque runtime) :
- **V1** : `docker:dind` privilégié (le plus répandu, compatibilité maximale) ;
- **V2** : `docker:dind-rootless` ;
- **V3** : Buildah/Podman sans privilège (build sans démon, alternative OpenShift) ;
- **V4** : BuildKit rootless (`buildctl`).

**Projets de référence** (au minimum 2, idéalement des projets réels de l'entreprise) :
- **P-JAVA** : Maven/Gradle, tests unitaires, tests d'intégration **Testcontainers** (PostgreSQL), packaging jar, Dockerfile multi-étapes ;
- **P-NODE** (ou Go/Python) : `npm ci`, lint, tests, build, Dockerfile multi-étapes, `docker compose` pour les tests e2e.

**Pipeline type** : checkout → restauration du cache → compilation → tests unitaires → tests d'intégration (conteneurs) → packaging → `docker build` (Dockerfile) → scan de l'image → `docker push` vers le registre → nettoyage.

| ID | Aspect | Test | Attendu runc | Attendu Kata | Env | Prio |
|---|---|---|---|---|---|---|
| DIND-01 | FUN | Démarrage du moteur de build (V1 à V4) dans le pod de CI : `docker info`, pilote de stockage, cgroups v2 | V1 OK en privilégié | V1 OK ; vérifier le pilote (overlay2 sur virtio-fs → `/var/lib/docker` sur emptyDir ou PVC bloc) | A | P1 |
| DIND-02 | FUN | **Jenkins** : pipeline complet P-JAVA et P-NODE sur un agent Kubernetes éphémère (`podTemplate` avec sidecar dind) | PASS | PASS, contournements notés | A | P1 |
| DIND-03 | FUN | **GitHub Actions / ARC** `dind` : workflow complet (`actions/checkout`, `setup-java`/`setup-node`, build, tests, `docker/build-push-action`) | PASS | PASS | A | P1 |
| DIND-04 | FUN | **GitHub Actions / ARC** `kubernetes` : jobs `container:` et `services:` (pods créés par les container hooks) | PASS | Pods de job aussi en Kata ? À vérifier | A | P2 |
| DIND-05 | FUN | Étape **Dockerfile** : multi-étapes, `--build-arg`, secrets de build (`--secret`), cache de build (`--cache-from`/registre), `buildx` multi-arch (amd64 + arm64 via QEMU/binfmt) | binfmt modifie le **noyau du nœud** | binfmt limité au noyau invité | A | P1 |
| DIND-06 | FUN | Tests qui lancent des conteneurs : **Testcontainers**, `docker compose up` pour l'e2e, `services:` GitHub | PASS | PASS ; vérifier le réseau Docker interne et la **MTU** (OVN-K 1400 vs bridge Docker 1500) | A | P1 |
| DIND-07 | FUN | Caches de build : `~/.m2`, `~/.npm`, couches Docker, sur PVC partagé (RWX) ou cache distant ; persistance entre jobs | PASS | PASS ; perf I/O à mesurer | A | P1 |
| DIND-08 | FUN | Push vers le registre (interne OpenShift, Quay, Artifactory) avec identifiants injectés ; scan de l'image produite | PASS | PASS | A | P2 |
| DIND-09 | FUN | Limites CPU/mémoire du job et des conteneurs internes, OOM d'une compilation lourde, `ephemeral-storage` | Cgroups imbriqués | Cgroups dans la VM, mémoire de la VM | A | P2 |
| DIND-10 | PERF | **Durée totale du pipeline** et par étape (compilation, tests, `docker build` froid/chaud, push), P-JAVA et P-NODE, n ≥ 5 | Référence | Δ par étape | A/B | P1 |
| DIND-11 | PERF | **Latence de prise en charge** : job en file → runner/agent prêt (création du pod + démarrage dind) | Référence | Δ mesuré | A/B | P1 |
| DIND-12 | PERF | `docker pull` d'images de base volumineuses (≥ 1 Go) et extraction des couches | Référence | Δ (I/O virtio) | A/B | P1 |
| DIND-13 | PERF | Concurrence : 5 / 10 / 20 jobs simultanés par nœud, durée moyenne, saturation, empreinte RAM/disque par job | Référence | Moins de jobs par nœud attendu | B | P1 |
| DIND-14 | SEC | **PR malveillante** (harnais rejoué dans une étape du pipeline) : depuis le pod de job ou un conteneur lancé par le dind interne avec `--privileged`, accès aux disques du nœud, `nsenter -t 1`, montage du FS du nœud, chargement de module | **Nœud compromis** | Confiné à la VM | A | P1 |
| DIND-15 | SEC | Isolation **entre jobs** : un job lit-il les secrets, le workspace, le cache ou les couches Docker d'un autre job (même nœud) ? Rémanence après un job éphémère | Accessible via le nœud si le job est privilégié | Isolé attendu | A | P1 |
| DIND-16 | SEC | Vol de secrets CI : token du runner GitHub / secret JNLP Jenkins, identifiants du registre, `GITHUB_TOKEN`, token du ServiceAccount. Accès au controller Jenkins ou à l'API Kubernetes | Dépend de la config | **Identique** : Kata ne protège pas les secrets donnés au pod ; RBAC et périmètre des tokens à vérifier | A | P1 |
| DIND-17 | SEC | **Empoisonnement de cache** : un job malveillant écrit dans le cache partagé (m2, npm, couches) utilisé par d'autres projets | Possible | Possible (indépendant du runtime) : cloisonnement des caches à prévoir | A | P2 |
| DIND-18 | SEC | Politique d'admission : `privileged: true` autorisé **seulement si** `runtimeClassName: kata` (ValidatingAdmissionPolicy + SCC dédiée au namespace CI) ; tentative de contournement | Refusé | Accepté | A | P1 |
| DIND-19 | SEC | Anti-pattern : socket du runtime du nœud (`/run/crio/crio.sock`) monté en hostPath | Contrôle total du nœud | **Reste un trou** même avec Kata : à interdire par politique | A | P2 |
| DIND-20 | SEC | Détection : un `docker run --privileged` ou un reverse shell lancé depuis un job est-il vu par Falco/RHACS ? Audit des builds | Vu (syscalls sur le nœud) | Angle mort probable | B | P2 |

### 6.7 Agents IA autonomes (AGT)

**Enjeu** : un agent autonome exécute du code généré par un LLM, potentiellement influencé par des contenus non fiables (*prompt injection* via un dépôt, une page web ou un ticket). Il faut le traiter comme du **code non fiable** : isolation forte, egress contrôlé, secrets hors de portée, arrêt d'urgence.

**Architecture de référence testée** :
- **Agent Sandbox** (`Sandbox`, `SandboxTemplate`, `SandboxWarmPool`, `SandboxClaim`) avec `runtimeClassName` runc ou kata.
- **Agent de référence** : Claude Agent SDK ou Claude Code en mode non interactif, dans l'image de sandbox (shell, Python, Node, git, Chromium headless).
- **Egress** : `EgressFirewall` OVN-K et `NetworkPolicy` *default deny*. Seules sorties autorisées : l'API du LLM et un miroir de paquets.
- **Secrets** : la clé API du LLM est injectée par un proxy d'egress et **n'est pas présente dans la sandbox**. On compare avec le mode naïf où la clé est en variable d'environnement.
- **Deux modes d'exécution** :
  - (a) LLM réel, pour le fonctionnel et la perf de bout en bout ;
  - (b) harnais rejoué (PREP-11), pour des tests de sécurité **déterministes**, qui ne dépendent pas de la bonne volonté du LLM.

Note : la plupart des contrôles de sécurité AGT (egress, secrets, RBAC) **ne dépendent pas du runtime**. On les teste quand même dans les deux runtimes, parce que le comité doit voir la défense en profondeur complète. Kata apporte la couche « évasion vers le nœud ».

| ID | Aspect | Test | Attendu runc | Attendu Kata | Env | Prio |
|---|---|---|---|---|---|---|
| AGT-01 | FUN | Cycle de vie : `Sandbox` → exécution d'outils → persistance (PVC) → arrêt/reprise → suppression | OK | OK | A | P1 |
| AGT-02 | FUN | `SandboxWarmPool` + `SandboxClaim` : attribution d'une sandbox préchauffée | OK | OK | A | P1 |
| AGT-03 | FUN | Outils typiques : `git clone`, `pip/npm install`, compilation, `pytest`, écriture de fichiers, serveur de dev exposé en interne | OK | OK | A | P1 |
| AGT-04 | FUN | Navigateur headless (Chromium/Playwright) : `/dev/shm`, sandbox seccomp de Chromium, captures | OK (souvent `--no-sandbox`) | À vérifier | A | P2 |
| AGT-05 | FUN | Agent qui a besoin de conteneurs (build/test via Podman ou Docker dans la sandbox, lien avec DIND) | Exige un pod privilégié | Faisable confiné | A | P2 |
| AGT-06 | FUN | Tâche de bout en bout avec LLM réel (ex. corriger un bug et faire passer les tests sur un dépôt de référence, n = 10) : taux de réussite | Référence | Identique attendu | A/B | P1 |
| AGT-07 | PERF | Latence de création d'une sandbox à froid (création → `Ready`) et via warm pool (claim → prête) | Référence | Δ mesuré ; le warm pool doit masquer le surcoût | A/B | P1 |
| AGT-08 | PERF | Latence d'un appel d'outil : 200 commandes courtes via `exec` (chemin API server → kubelet → CRI → agent Kata) | Référence | Δ mesuré | A/B | P1 |
| AGT-09 | PERF | Durée des tâches outillées : `pip install` d'un projet lourd, `npm ci`, suite de tests | Référence | Δ mesuré (I/O) | A/B | P1 |
| AGT-10 | PERF | Densité : 10 / 25 / 50 sandboxes d'agents actives sur un nœud, mémoire par sandbox, saturation | Référence | Moins de sandboxes attendu (overhead VM) | B | P1 |
| AGT-11 | PERF | Part du runtime dans la durée totale d'une tâche (temps LLM vs temps d'exécution des outils), pour relativiser l'overhead Kata | — | Calculée | A/B | P1 |
| AGT-12 | SEC | *Prompt injection* : un README piégé demande d'exfiltrer l'environnement et les fichiers vers un domaine externe (LLM réel + harnais) | Egress bloqué | Egress bloqué | A | P1 |
| AGT-13 | SEC | Secrets : l'agent tente de lire la clé API (env, fichiers, mémoire du processus, proxy) ; comparaison clé en env vs proxy d'injection | Clé lisible en mode naïf | Idem : **Kata ne protège pas les secrets donnés au pod** | A | P1 |
| AGT-14 | SEC | Accès à l'API Kubernetes : token de ServiceAccount (`automountServiceAccountToken: false`), RBAC, endpoints de métadonnées | Bloqué | Bloqué | A | P1 |
| AGT-15 | SEC | Évasion depuis la sandbox, agent root dans le conteneur : scénarios SEC-03/04/06/08 rejoués par le harnais | Surface = noyau du nœud | Surface = noyau invité + hyperviseur | A | P1 |
| AGT-16 | SEC | Mouvement latéral : scan du réseau du cluster, accès aux autres sandboxes, aux services internes, au nœud | Bloqué par NetworkPolicy | Idem | A | P1 |
| AGT-17 | SEC | Abus de ressources : fork bomb, minage simulé (CPU 100 %), remplissage disque, fuite mémoire. Confinement et impact sur les autres sandboxes | Contenu par cgroups | Contenu par VM + cgroups | A/B | P1 |
| AGT-18 | SEC | Fuite entre sessions : une sandbox recyclée par le warm pool contient-elle des données d'un utilisateur précédent ? | Aucune donnée | Aucune donnée | A | P1 |
| AGT-19 | SEC | Traçabilité : les commandes de l'agent sont-elles auditées (audit log API pour `exec`, logs de l'agent, détection runtime Falco/RHACS) ? | Visible | Angle mort probable côté nœud | A/B | P1 |
| AGT-20 | SEC | Arrêt d'urgence : délai entre `delete sandbox` et l'arrêt effectif de tous les processus de l'agent, y compris ceux qui ignorent SIGTERM | Mesuré | Mesuré (arrêt de la VM) | A | P1 |

### 6.9 Volumes et stockage (VOL)

**Enjeu** : avec runc, un volume monté par le kubelet est visible tel quel dans le conteneur. Avec Kata, le volume est monté **sur le nœud**, puis transmis à la VM. Le transport dépend du mode du volume :
- `Filesystem` : partage **virtio-fs**. Chaque accès traverse le démon `virtiofsd` ; la sémantique POSIX peut changer (verrous, xattr, inotify, mmap). ENV-A a déjà montré la perte des xattr (DIND) et l'échec d'overlay.
- `Block` : périphérique **virtio-blk** branché à chaud dans la VM ; le système de fichiers est monté par le noyau invité.
- Volumes montés **par le pod lui-même** (NFS, CIFS, FUSE) : le montage a lieu dans le noyau invité. Il faut les modules dans ce noyau et `/dev/fuse` dans la VM (constat ENV-A : non fourni par défaut).

**Backends testés** :

| Backend | Accès | ENV-A (CRC, banc) | Cluster distant |
|---|---|---|---|
| **local** | PV `local` / hostpath-provisioner (Filesystem) ; LVMS / TopoLVM (Block et Filesystem) | `kubevirt-hostpath-provisioner` de CRC ; LVMS si un disque est disponible | StorageClass locale existante |
| **NFS** | CSI `csi-driver-nfs` (RWX) ; montage NFS dans le pod | Serveur NFS dans le cluster + CSI | Serveur NFS d'entreprise + StorageClass existante |
| **CIFS / SMB** | CSI `csi-driver-smb` (RWX, identifiants dans un Secret) ; montage CIFS dans le pod | Serveur Samba dans le cluster + CSI | Partage SMB d'entreprise (AD) + StorageClass existante |
| **S3** | (a) SDK / API, sans volume ; (b) CSI FUSE (Mountpoint for S3 CSI ou `csi-s3`), FUSE **sur le nœud** ; (c) FUSE **dans le pod** (`s3fs`, `rclone mount`) | MinIO dans le cluster | Endpoint S3 d'entreprise (ou ODF/NooBaa) |

Les identifiants des backends ne sont **jamais** dans le dépôt. `campaign.yaml` ne référence que des Secrets existants (voir PREP-14).

| ID | Aspect | Test | Attendu runc | Attendu Kata | Env | Prio |
|---|---|---|---|---|---|---|
| VOL-01 | FUN | **Matrice de base**, pour chaque backend et chaque mode d'accès : provisionnement, montage, écriture et relecture (somme de contrôle), redémarrage du pod puis relecture | OK | À vérifier par backend | A | P1 |
| VOL-02 | FUN | **Droits** : `runAsUser` arbitraire (SCC `restricted-v2`), `fsGroup` + `fsGroupChangePolicy`, `root_squash` NFS, `uid`/`gid`/`file_mode` CIFS, contexte SELinux (`seLinuxMount`, `context=`) | OK | À vérifier (traduction des droits par virtio-fs) | A | P1 |
| VOL-03 | FUN | **Partage RWX simultané** entre un pod runc et un pod Kata (NFS, CIFS, S3 CSI) : visibilité des écritures et délai, `inotify` sur des changements faits par l'autre pod | Visibles | Visibles ; `inotify` probablement aveugle aux écritures externes | A | P1 |
| VOL-04 | FUN | **Verrous** entre deux pods : `flock`, `fcntl` (POSIX), verrous d'octets ; SQLite sur volume partagé | Conformes au backend | À vérifier (verrous traversant virtio-fs) | A | P1 |
| VOL-05 | FUN | **Sémantique POSIX** sur chaque backend : `fsync`, `O_DIRECT`, `mmap` partagé, `rename` atomique, liens durs et symboliques, xattr, fichiers creux, noms longs ou non ASCII | Référence | Écarts listés | A | P1 |
| VOL-06 | FUN | **Cycle de vie CSI** : extension en ligne, snapshot et clone (si le driver le permet), replanification sur un autre nœud, suppression du pod pendant des écritures | OK | À vérifier (extension visible dans la VM ?) | A/B | P2 |
| VOL-07 | FUN | **Volume `Block`** (LVMS / TopoLVM, ou `local` en mode bloc) : `mkfs` et montage dans le pod, I/O directes | OK | Périphérique virtio-blk dans la VM | A | P2 |
| VOL-08 | FUN | **Montage dans le pod**, sans CSI : `mount -t nfs`, `mount -t cifs`, `s3fs` / `rclone mount` (FUSE) ; privilèges nécessaires dans chaque runtime | Exige des privilèges sur le nœud | Modules NFS/CIFS du noyau invité ? `/dev/fuse` absent (constat ENV-A) | A | P2 |
| VOL-09 | FUN | **S3 par API** (`aws s3`, `mc`) : envoi multipart d'un gros objet, CA d'entreprise, proxy ; référence indépendante du runtime | OK | Identique | A | P2 |
| VOL-10 | PERF | **Débit et latence par backend** (`fio`) : séquentiel 1M, aléatoire 4k, latence p99 ; **métadonnées** (création, `stat`, suppression de 10 000 petits fichiers) ; `git clone` et `npm ci` sur le volume | Référence | Δ par backend (surcoût de virtio-fs) | A/B | P1 |
| VOL-11 | PERF | **Démarrage** : délai jusqu'à Ready avec 0, 1 et 5 volumes de chaque type | Référence | Δ mesuré | A/B | P2 |
| VOL-12 | SEC | **Visibilité des autres montages** depuis un pod compromis (privilégié) : autres PVC du nœud, répertoires du kubelet, montages NFS/CIFS d'autres pods | Tous accessibles | Seulement les volumes du pod (vérifier) | A | P1 |
| VOL-13 | SEC | **Identifiants des backends** : CIFS (Secret du CSI), clés S3, Kerberos. Où se trouvent-ils (nœud, pod), qui peut les lire, présence dans `oc describe`, dans les événements et dans `/proc/mounts` | Selon le mode | Idem ; en montage dans le pod, les identifiants sont dans la VM | A | P1 |
| VOL-14 | FUN | **Propagation de montage** (`mountPropagation: HostToContainer` / `Bidirectional`), utilisée par certains agents de stockage et de sécurité | OK | Limite attendue | A | P3 |
| VOL-15 | OPS | **Perte du serveur** NFS / CIFS / S3 pendant des I/O (montage `hard`), puis retour : état du pod, suppression possible, impact sur la VM et sur le nœud, reprise | Processus bloqués (état D) | À mesurer (pod bloqué en `Terminating` ?) | A | P1 |

Liens : FUN-02 à FUN-06 (volumes génériques), PERF-10 (I/O `emptyDir` et PVC). Les tests VOL les approfondissent par backend.

### 6.10 Secrets (SCR)

**Enjeu** : un secret natif monté en volume est stocké en **tmpfs sur le nœud**. Avec Kata, il est en plus **copié dans la VM** : l'agent Kata surveille ces montages et recopie les mises à jour. Cette copie a des limites (nombre et taille des fichiers, à vérifier selon la version) au-delà desquelles Kata revient à virtio-fs. Un gestionnaire externe (Vault, Conjur) ajoute ses propres chemins : sidecar qui écrit dans un `emptyDir`, driver CSI qui écrit **sur le nœud**, ou synchronisation vers un Secret natif. Le runtime peut changer leur comportement : propagation des rotations, mémoire de la VM consommée par le sidecar, `exec` dans le conteneur.

**Kata ne protège pas les secrets contre l'administrateur du nœud** : ils restent lisibles dans le tmpfs du nœud et dans la mémoire de la VM. Seuls les *confidential containers* (VM chiffrées) changent ce point. Les tests le vérifient au lieu de le supposer.

**Fournisseurs testés** :

| Fournisseur | Modes d'intégration | Authentification de la charge | ENV-A (CRC, banc) | Cluster distant |
|---|---|---|---|---|
| **Secret Kubernetes natif** | variable d'environnement, volume, volume projeté, `subPath`, secret immuable | — | — | — |
| **HashiCorp Vault** | Vault Agent Injector (init + sidecar) ; Vault CSI Provider (Secrets Store CSI Driver) ; Vault Secrets Operator ou External Secrets Operator (synchronisation vers un Secret natif) | méthode `kubernetes` (token de ServiceAccount) ou `jwt` | Vault en mode dev (Helm) + injector + CSI provider | Instance d'entreprise, *namespace* et rôle de test dédiés |
| **CyberArk Conjur** | Secrets Provider for Kubernetes : init, sidecar, modes « K8s Secrets » et « Push to File » ; Conjur CSI Provider ; External Secrets Operator ; Secretless Broker (P3) | `authn-jwt` (token de ServiceAccount) ; `authn-k8s` (certificat **injecté dans le conteneur par `exec`**) | Conjur OSS (Helm), si les images existent en arm64 (sinon ENV-B seulement) | Conjur Enterprise ou Cloud, *host* et *policy* de test dédiés |

Chaque test SCR-10 à SCR-18 (aspect OPS = robustesse en cas de panne) est exécuté **pour Vault et pour Conjur** (variantes du plan), et pour chaque mode d'intégration supporté.

| ID | Aspect | Test | Attendu runc | Attendu Kata | Env | Prio |
|---|---|---|---|---|---|---|
| SCR-01 | FUN | **Secret natif, tous les modes** : variable d'environnement, volume, projeté, `subPath`, `items`, `optional`, immuable ; contenu binaire et taille proche de 1 MiB ; contenu identique octet par octet | OK | OK, à vérifier pour les gros secrets | A | P1 |
| SCR-02 | FUN | **Rotation d'un secret natif** : délai de propagation dans le volume ; `subPath` et variables d'environnement non mis à jour (attendu dans les deux runtimes) ; secret avec beaucoup de clés ou volumineux (au-delà des limites de copie de l'agent Kata) | Délai du kubelet (≤ 1–2 min) | Délai du kubelet + copie de l'agent ; repli virtio-fs au-delà des limites | A | P1 |
| SCR-03 | FUN | **Token de ServiceAccount projeté** : audience, `expirationSeconds: 600`, rotation du fichier, utilisation par Vault et Conjur (`jwt`) | Rotation OK | Rotation propagée dans la VM ? | A | P1 |
| SCR-04 | SEC | **Où vit le secret** : tmpfs du nœud, mémoire de la VM, variables d'environnement visibles dans `/proc/<pid>/environ` depuis le nœud ; lisibilité par un administrateur du nœud | Lisible depuis le nœud | **Lisible aussi** (tmpfs du nœud, mémoire de QEMU) : Kata ne protège pas contre le nœud | A | P1 |
| SCR-05 | SEC | **Collecte depuis un pod privilégié** du même nœud : lecture des secrets des autres pods (`/var/lib/kubelet/pods/*/volumes/kubernetes.io~secret`, `~csi`). Matrice attaquant runc / Kata × victime runc / Kata | Attaquant runc : tous lus | Attaquant Kata : aucun (frontière VM). Victime Kata attaquée depuis runc : lue | A | P1 |
| SCR-06 | SEC | **Exposition dans le pod** : un conteneur applicatif peut-il lire le token du sidecar (Vault Agent, Conjur) ; `shareProcessNamespace` ; fuite dans les logs, dans `oc describe` et dans les événements | Selon la configuration | Identique | A | P2 |
| SCR-10 | FUN | **Injection par sidecar / init** : Vault Agent Injector (annotations, template) ; Conjur Secrets Provider en init et en sidecar (Push to File). Le webhook mute le pod Kata ; le fichier est rendu dans un `emptyDir` en mémoire | OK | OK attendu ; **mémoire de la VM** à prévoir pour le sidecar (constat ENV-A n° 2) | A | P1 |
| SCR-11 | FUN | **Secrets Store CSI Driver** (Vault CSI Provider, Conjur CSI Provider) : montage, synchronisation optionnelle vers un Secret natif, **rotation** (`enableSecretRotation`) : propagation jusqu'au processus | OK | Écriture sur le nœud, puis virtio-fs : propagation à mesurer | A | P1 |
| SCR-12 | FUN | **Synchronisation vers un Secret natif** : Vault Secrets Operator, External Secrets Operator, Conjur « K8s Secrets » ; redémarrage automatique du Deployment lors d'une rotation | OK | Identique (retour au cas natif SCR-02) | A | P2 |
| SCR-13 | FUN | **Authentification de la charge** : Vault `kubernetes` et `jwt` ; Conjur `authn-jwt` et **`authn-k8s`**, dont le certificat est injecté par `exec` dans le conteneur (chemin `exec` différent avec Kata) | OK | `authn-k8s` à vérifier en priorité | A | P1 |
| SCR-14 | FUN | **Rotation et secrets dynamiques** : secret KV modifié, identifiants de base de données dynamiques (Vault) ou rotation de mot de passe (Conjur), sur plus de 2 TTL ; renouvellement des baux | Valeur à jour dans le délai configuré | Idem, délai mesuré | A | P1 |
| SCR-15 | PERF | **Coût au démarrage** : délai jusqu'à Ready en natif, avec injector, avec CSI et avec synchronisation ; latence d'obtention du secret ; mémoire ajoutée par le sidecar | Référence | Δ mesuré (sidecar = mémoire de VM en plus) | A/B | P1 |
| SCR-16 | SEC | **Moindre privilège** : un pod du rôle A ne lit pas les chemins du rôle B ; un ServiceAccount volé dans un autre namespace est refusé ; journal d'audit Vault / Conjur rattaché à l'identité du pod | Refusé, audité | Identique | A | P1 |
| SCR-17 | SEC | **Rémanence** : après suppression du pod, le secret reste-t-il sur le nœud (tmpfs, cache CSI, `emptyDir`) ou dans la mémoire libérée ? | Nettoyé | Nettoyé (arrêt de la VM) | A | P2 |
| SCR-18 | OPS | **Indisponibilité** du fournisseur (Vault scellé ou arrêté, Conjur arrêté) au démarrage du pod et pendant son exécution : blocage de l'init, dernière valeur conservée par le sidecar, reprise | Comportement documenté | Identique attendu | A | P1 |

Liens : FUN-04 (mise à jour à chaud des ConfigMap et Secret), SEC-12 (isolation des secrets entre pods), AGT-13 (clé d'API de l'agent), DIND-16 (secrets de CI).

## 7. Critères d'évaluation et pondération (proposition à valider par le comité)

| Domaine | Poids | Critères |
|---|---|---|
| Sécurité / isolation | 35 % | SEC et POL P1 réussis, réduction de la surface d'attaque, angles morts de détection |
| Compatibilité fonctionnelle | 25 % | % de tests FUN P1 en PASS, workloads de réf. OK sans modification |
| Performance / coût | 20 % | Overhead de démarrage, mémoire, densité, I/O, réseau |
| Exploitabilité | 15 % | Installation, upgrade, observabilité, debug, compatibilité avec les policies d'admission (POL) |
| Support / maturité | 5 % | Support éditeur, roadmap, communauté |

Chaque domaine est noté de 1 à 5 pour chaque runtime (grille dans `03-FORMAT-RAPPORT.md` §5).

Les cas d'usage **DIND** et **AGT** reçoivent en plus leur **propre fiche de décision** : un tableau Fonctionnel / Performance / Sécurité par runtime et un verdict « recommandé / acceptable avec conditions / déconseillé ». Le comité a besoin d'une réponse par cas d'usage, pas seulement d'un score global.

## 8. Critères d'entrée / de sortie

- **Entrée** : PREP-01 à PREP-07 validés sur l'environnement concerné.
- **Sortie** : 100 % des tests P1 exécutés (statut ≠ `BLOCKED`), ≥ 80 % des P2, rapport généré et relu, limites consolidées, recommandation rédigée.

## 9. Planning indicatif

| Semaine | Activité | Env |
|---|---|---|
| S1 | PREP sur ENV-A (dont Agent Sandbox, backend LLM, harnais rejoué), image `kata-bench`, scripts | A |
| S2 | FUN + SEC + LIM sur ENV-A | A |
| S3 | CI (Jenkins, GitHub Actions) + AGT, fonctionnel et sécurité, sur ENV-A | A |
| S4 | Provisionnement ENV-B, PREP, PERF + OPS + perf DIND/AGT | B |
| S5 | Rejeu des tests P1 sur ENV-B, agrégation, rédaction, revue | B |
| S6 | Présentation au comité | — |

## 10. Risques

| Risque | Impact | Mitigation |
|---|---|---|
| Nested virt instable / non activable sur CRC | Pas de tests Kata sur A | Option C (poste x86) ou accélérer ENV-B |
| Chiffres de perf ENV-A non représentatifs | Mauvaise décision | Ne présenter que les chiffres ENV-B ; marquer A comme « indicatif » |
| Kata upstream ≠ OSC | Écarts de comportement | Rejeu des P1 sur ENV-B avec OSC |
| Ressources CRC insuffisantes | Tests de densité impossibles | Densité uniquement sur ENV-B |
| `agent-sandbox-operator` en *preview* (v0.9) et amd64 uniquement | API instable, pas supporté en prod | Upstream sur ENV-A ; statut de support documenté dans OPS-09 |
| Non-déterminisme du LLM | Tests de sécurité AGT non reproductibles | Harnais rejoué (PREP-11) pour SEC ; LLM réel seulement pour le fonctionnel et la perf de bout en bout |
| Accès GitHub (App/PAT) et sortie Internet depuis CRC pour ARC | Tests GitHub Actions bloqués | Organisation/dépôt de test dédié ; à défaut GitHub Enterprise Server interne |
| Coût et confidentialité des appels au LLM distant | Budget, fuite de données de test | Dépôts de test synthétiques, budget de tokens plafonné, ou modèle local |

## 11. Arborescence du dépôt de campagne

```
kata/
├── 01-ENVIRONNEMENT.md
├── 02-PLAN-DE-TESTS.md
├── 03-FORMAT-RAPPORT.md
├── pyproject.toml      # dépendances Python (uv sync / uv run)
├── schemas/            # result.schema.json (format des résultats bruts)
├── precheck, run, setup # points d'entrée (voir README)
├── policies/kyverno/   # catalogue de policies Kyverno
├── scripts/            # moteur kvr/, validate_results.py, (à venir) aggregate.py, render-report.py
├── images/kata-bench/  # Containerfile de l'image d'outillage
├── images/agent-sandbox/ # image de sandbox agent (shell, python, node, git, chromium, agent)
├── ci/                 # values Helm Jenkins/ARC, podTemplates, workflows, Jenkinsfiles de référence
├── harness/            # harnais « agent rejoué » + séquences d'appels d'outils (bénignes / malveillantes)
├── tests/<ID>/         # pod.tmpl.yaml, run.sh, README (procédure + critère)
├── results/<campagne>/<ENV>/<ID>/<runtime>/run-<n>.json
└── report/             # rapport généré (md, html, pdf) + graphiques
```
