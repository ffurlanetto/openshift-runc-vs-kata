# runc ou Kata Containers sur OpenShift : rapport au comité

| | |
|---|---|
| Version | 1.0 (ENV-A) |
| Date | 24 novembre 2026 |
| Statut | **Brouillon pour revue** : résultats ENV-A (poste de travail), à confirmer sur ENV-B (bare metal x86_64) |
| Diffusion | Comité d'architecture, équipes plateforme, sécurité, CI et IA |
| Données | [Fiches de test générées](donnees.md) · [Plan de tests](../02-PLAN-DE-TESTS.md) · [Environnement](../01-ENVIRONNEMENT.md) · résultats bruts dans `results/`, preuves dans `evidence/` |

---

## 1. Synthèse décisionnelle

**Recommandation** : garder **runc par défaut** et réserver **Kata** aux charges qui ont besoin d'une frontière forte avec le nœud : builds CI qui exigent des privilèges, agents IA qui exécutent du code non relu, charges multi-tenants non fiables. Kata doit être **imposé par une policy d'admission**, jamais laissé au choix du pod, et ne remplace aucun des autres contrôles (admission, SELinux, egress, gestion des secrets).

**Constats clés (ENV-A, Kata 4.4.0, shims Rust et Go)**

1. **Kata protège le nœud contre un pod privilégié.** Un pod privilégié runc atteint le nœud par 5 techniques sur 2 profils (SEC-04), modifie un sysctl du nœud et y charge un module noyau (SEC-09), monte le disque d'un autre pod (VOL-12) et lit les secrets des autres pods (SCR-05). En Kata, **aucune** de ces actions n'atteint le nœud ni les autres pods : elles restent dans la VM. Le résultat est identique avec les deux shims.
2. **Kata ne protège pas le pod contre le nœud.** Un administrateur du nœud lit la mémoire, les fichiers et le trafic réseau d'un pod Kata comme ceux d'un pod runc (SEC-18, SCR-04). Seule la visibilité du processus change. Protéger le pod contre l'hôte relève des *Confidential Containers* (CoCo), hors périmètre.
3. **L'isolation entre pods voisins est identique.** Aucun voisin, runc ou Kata, ne voit les processus, la mémoire ni les fichiers d'un autre pod (SEC-18). L'escalade de privilèges dans le pod est bloquée à l'identique (SEC-19).
4. **Trois garde-fous de runc disparaissent ou changent en Kata** et doivent être compensés :
   - aucun filtre seccomp dans le conteneur (SEC-08, POL-17) ;
   - la limite `ephemeral-storage` n'est pas appliquée, le pod n'est pas évincé (POL-16) ;
   - avec le shim Rust, l'OOM est signalé `Error` et non `OOMKilled` (FUN-17), ce qui aveugle la supervision.
5. **Coût de démarrage élevé (en virtualisation imbriquée).** Pod prêt en 20,6 s (Rust) et 30,9 s (Go) contre 0,65 s en runc (PERF-01, médiane sur 30 runs). Un exec d'outil coûte environ 240 ms contre 60 ms (AGT-08). Ces chiffres sont **pessimistes** et seront remesurés sur ENV-B.

**Décision demandée au comité**

- Valider le principe « runc par défaut, Kata imposé par policy pour les classes de charges listées au §8 ».
- Autoriser la campagne ENV-B (bare metal, OpenShift Sandboxed Containers) pour confirmer les performances et les écarts de supervision avant un pilote.
- Désigner un propriétaire pour les trois écarts du constat 4 (seccomp, `ephemeral-storage`, OOM).

---

## 2. Contexte et périmètre

**Objectif** : comparer runc (runtime par défaut d'OpenShift) et Kata Containers (pod dans une micro-VM) sur la sécurité, le fonctionnel, la performance et l'exploitation, et en particulier pour deux cas d'usage : la CI qui construit des images (Docker-in-Docker et variantes) et les agents IA autonomes.

**Deux implémentations de Kata sont comparées** :

| RuntimeClass | Shim | Statut |
|---|---|---|
| `kata` | `kata-qemu-runtime-rs` (Rust) | défaut de kata-deploy 4.4 |
| `kata-qemu` | `kata-qemu` (Go) | implémentation historique, base d'OpenShift Sandboxed Containers |

Dans ce rapport, « Kata » désigne les deux shims quand leur comportement est identique ; sinon le shim est précisé.

**Environnement ENV-A** : OpenShift Local (CRC) 4.22.1, un nœud arm64 de 12 vCPU et 24 Go, dans une VM sur Mac, donc **virtualisation imbriquée**. Kata 4.4.0 installé par kata-deploy (pas OpenShift Sandboxed Containers), QEMU, noyau invité 6.18.62. Kyverno 1.20.0. Détails : [01-ENVIRONNEMENT](../01-ENVIRONNEMENT.md).

> **Avertissement** : ENV-A sert à valider le comportement et le banc de test. Les **constats fonctionnels et de sécurité** sont représentatifs. Les **mesures de performance** ne le sont pas : la virtualisation imbriquée les dégrade fortement.

**Hors périmètre** : Confidential Containers, peer-pods, Windows, GPU, attaques par canaux auxiliaires (cache, timing).

**Méthode** : 163 tests au plan, dont 44 automatisés, tous exécutés ici. Banc rejouable (`./precheck`, `./run`), chaque run produit un JSON validé par schéma et des preuves brutes. Mode sûr par défaut : les tests intrusifs (`--non-safe`) ont été exécutés uniquement sur ce cluster personnel. Toutes les données publiées sont anonymisées.

---

## 3. Tableau de bord

### 3.1 Couverture et statuts

Statut le plus défavorable sur l'ensemble des runs mesurés, par test et par variante (détail : [donnees.md](donnees.md)).

| Domaine | Tests (variantes) | runc PASS | Kata Rust PASS / PARTIAL / FAIL / NON SUPP. | Kata Go PASS / PARTIAL / FAIL / NON SUPP. |
|---|---|---|---|---|
| Fonctionnel | 2 | 2 | 0 / 1 / 0 / 1 | 1 / 0 / 0 / 1 |
| Performance | 1 | 1 | 1 / 0 / 0 / 0 | 1 / 0 / 0 / 0 |
| Sécurité | 8 | 8 | 6 / 1 / 1 / 0 | 6 / 1 / 1 / 0 |
| Policies d'admission (Kyverno) | 18 | 18 | 16 / 0 / 2 / 0 | 16 / 0 / 2 / 0 |
| CI dans Kata (DIND) | 4 (15) | 15 | 4 / 0 / 5 / 6 | 5 / 0 / 6 / 4 |
| Agents IA | 4 | 4 | 4 / 0 / 0 / 0 | 3 / 0 / 1 / 0 |
| Volumes | 2 | 2 | 2 / 0 / 0 / 0 | non mesuré |
| Secrets | 5 | 5 | 5 / 0 / 0 / 0 | non mesuré |

Lecture des statuts pour les tests de sécurité : **PASS = comportement conforme à l'attendu du plan**, y compris quand l'attendu est « runc atteint le nœud ». Un PASS runc sur SEC-04 signifie donc que l'évasion a bien été démontrée.

### 3.2 Indicateurs clés

| Indicateur | runc | Kata Rust | Kata Go | Tests |
|---|---|---|---|---|
| Pod prêt, médiane (p5–p95) | 0,65 s (0,45–1,5) | 20,6 s (19,6–21,7) | 30,9 s (22,3–60,7) | PERF-01, 30 runs |
| Exec d'un outil, p50 / p95 | 61 / 75 ms | 237 / 318 ms | 287 / 489 ms | AGT-08, 3×100 exec |
| Overhead déclaré par pod | 0 | 250m CPU, 320 Mi | 250m CPU, 320 Mi | POL-12 |
| Noyau partagé avec le nœud | oui | non | non | SEC-01 |
| Techniques d'évasion d'un pod privilégié réussies | 5 | 0 | 0 | SEC-04 |
| Sysctl / module noyau du nœud modifiables par un pod privilégié | oui / oui | non / non | non / non | SEC-09 |
| Volume d'un autre pod atteint par un pod privilégié | oui | non | (non mesuré) | VOL-12 |
| Secrets d'autres pods volés (hostPath kubelet en lecture) | oui | non | (non mesuré) | SCR-05 |
| Voisin qui voit processus / mémoire / fichiers d'un pod | non | non | non | SEC-18 |
| Administrateur du nœud qui lit mémoire / fichiers / réseau du pod | oui | oui | oui | SEC-18, SCR-04 |
| Filtre seccomp actif dans un pod restreint | oui | **non** | **non** | SEC-08, POL-17 |
| Limite CPU respectée | oui (0,50 cœur) | oui | oui | POL-15 |
| Limite `ephemeral-storage` appliquée (éviction) | oui (80 s) | **non** | **non** | POL-16 |
| OOM signalé `OOMKilled` | oui (1,5 s) | **non** (`Error`, 26 s) | oui (55 s) | FUN-17 |
| Policies Kyverno appliquées à l'identique | 18/18 | 18/18 à l'admission | 18/18 à l'admission | POL-01..18 |
| Kata imposable par policy (mutation + overhead) | — | oui | oui | POL-12 |
| `hostNetwork` | oui | non supporté, **admis par le cluster** | idem | FUN-30, POL-18 |
| Build d'image : variantes qui fonctionnent | 5/5 | 1/5 (dind privilégié, stockage en mémoire) | 1/5 | DIND-05 |
| Étape CI malveillante qui atteint le disque du nœud | oui | non | non | DIND-14 |
| Arrêt d'un processus qui ignore SIGTERM | 8,3 s | 3,4 s | 4,5 s | AGT-20 |
| Rotation d'un secret visible dans le pod | 2,3 s | 85,6 s | (non mesuré) | SCR-02 |

### 3.3 Notation pondérée (ENV-A, provisoire)

| Domaine | Poids | runc | Kata | Justification |
|---|---|---|---|---|
| Sécurité / isolation | 35 % | 3 | 4 | runc : évasion avec pod privilégié (SEC-04, SEC-09, VOL-12, SCR-05). Kata : pas d'évasion vers le nœud, mais seccomp absent (SEC-08) et pod non protégé de l'hôte (SEC-18) |
| Compatibilité fonctionnelle | 25 % | 5 | 3 | Kata : `hostNetwork` non supporté, 4 variantes de build sur 5 en échec (DIND), `ephemeral-storage` non appliqué (POL-16) |
| Performance / coût | 20 % | 5 | 1 (indicatif) | Δ > 100 % au démarrage et à l'exec (PERF-01, AGT-08) en virtualisation imbriquée ; à remesurer sur ENV-B |
| Exploitabilité | 15 % | 5 | 3 | Motif OOM différent (FUN-17, Rust), rotation des secrets plus lente (SCR-02), admission à durcir (POL-11, POL-18) |
| Support / maturité | 5 % | 5 | 3 | kata-deploy upstream ; le support Red Hat passe par OpenShift Sandboxed Containers (à évaluer sur ENV-B) |
| **Score pondéré** | 100 % | **4,3** | **3,1** | Score attendu en hausse sur ENV-B pour la performance |

Le score global favorise runc parce qu'il agrège des critères qui ne pèsent pas pareil pour chaque charge. La décision se prend par classe de charge (§8), pas sur ce score.

---

## 4. Résultats par domaine

### 4.1 Sécurité et isolation

**Ce que Kata apporte : une frontière entre le pod et le nœud.**

| Scénario | runc | Kata (Rust et Go) | Test |
|---|---|---|---|
| Noyau vu par le pod | celui du nœud (5.14 RHCOS) | celui de la VM (6.18) | SEC-01 |
| Ressources visibles depuis un pod restreint | 12 CPU, 24 Go (tout le nœud) | 1 à 2 CPU, 0,3 à 2,2 Go (la VM) | SEC-03 |
| Pod privilégié : évasion vers le nœud | 5 techniques réussies, témoin trouvé sur le nœud | 0 : chaque technique n'atteint que la VM | SEC-04 |
| Pod privilégié : sysctl et module noyau | appliqués au nœud (restaurés) | appliqués à la VM seulement ; module du nœud refusé | SEC-09 |
| Pod privilégié : disques et volumes des autres pods | 4 périphériques montés, volume de la victime lu | 1 disque (celui de la VM), volume non atteint | VOL-12 |
| Pod compromis : secrets des autres pods (hostPath kubelet) | volés, y compris ceux d'un pod Kata | aucun secret lu | SCR-05 |
| Étape CI malveillante dans un dind privilégié | disque du nœud monté | seul le disque de la VM | DIND-14 |

Chaque constat d'évasion est vérifié par une **sonde runc distincte** sur le même nœud, et chaque modification est annulée puis vérifiée. Aucun résidu n'a été laissé (métriques `node_left_modified`, `node_settings_not_restored` à 0).

**Ce que Kata n'apporte pas : la protection du pod contre le nœud.**

| Scénario | runc | Kata | Test |
|---|---|---|---|
| Voisin (runc ou même runtime) qui voit processus, mémoire, fichiers | non | non | SEC-18 |
| Administrateur du nœud : processus du pod visible par son nom | oui | non (seuls QEMU, virtiofsd, le shim apparaissent) | SEC-18 |
| Administrateur du nœud : mémoire du pod lisible | oui | oui (mémoire de la VM) | SEC-18, SCR-04 |
| Administrateur du nœud : fichiers et trafic réseau du pod | oui | oui | SEC-18 |
| Secret monté lisible depuis le nœud (tmpfs kubelet) | oui | oui | SCR-04 |

**Garde-fous internes au pod.**

| Contrôle | runc | Kata | Test |
|---|---|---|---|
| Filtre seccomp `RuntimeDefault` | actif ; 3 appels sensibles sur 18 atteignent le noyau du nœud | **absent** ; 11 sur 18 atteignent le noyau de la VM | SEC-08, POL-17 |
| `no_new_privs`, capacités effectives nulles, uid non root | oui | oui | SEC-19, POL-17 |
| Escalade par binaire setuid avec `allowPrivilegeEscalation: false` | bloquée | bloquée | SEC-19 |
| Espace de noms utilisateur depuis un pod restreint | refusé | **autorisé** (conséquence de l'absence de seccomp, limité à la VM) | SEC-19 |

L'absence de seccomp ne permet pas d'atteindre le nœud (la frontière est la VM), mais elle **élargit la surface du noyau invité** et supprime une défense en profondeur. Avec kata-deploy, le shim n'applique pas le profil seccomp du pod dans l'invité. À vérifier avec OpenShift Sandboxed Containers sur ENV-B.

**hostPath (SEC-05).** En runc, un pod root non privilégié avec un hostPath n'a accès au répertoire que si son contexte SELinux le permet. Avec le contexte par défaut (`container_t`), l'accès est refusé ; avec `spc_t`, la lecture et l'écriture sont vues par le nœud. Un hostPath de `/` en lecture seule ne protège pas les points de montage imbriqués : l'écriture dans `/var/tmp` du nœud a réussi (comportement connu de Kubernetes, corrigé par `recursiveReadOnly`). En Kata (Rust et Go), **aucun pod hostPath non privilégié n'a démarré** : l'agent refuse la création du conteneur (`Permission denied`). Kata est donc ici plus restrictif, mais par effet de bord, pas par conception. La protection contre les hostPath doit rester à l'admission (SCC, Kyverno POL-08).

### 4.2 Fonctionnel

| Point | runc | Kata | Test |
|---|---|---|---|
| OOM sur dépassement de `limits.memory` | `OOMKilled` en 1,5 s | Rust : tué (137) mais motif **`Error`**, 26 s · Go : `OOMKilled`, 55 s | FUN-17 |
| `hostNetwork` | fonctionne | **non supporté**, mais **admis** par le cluster : le test n'est pas exécuté car il peut rendre le nœud indisponible | FUN-30, POL-18 |
| Volume persistant local : montage, écriture, persistance | oui (xfs) | oui (via virtio-fs) | VOL-01 |
| Secrets natifs : tous les modes de consommation | oui | oui | SCR-01 |
| Rotation d'un secret monté | 2,3 s | 85,6 s | SCR-02 |
| Rotation du token de ServiceAccount projeté | après ~530 s, accepté | après ~500 s, accepté | SCR-03 |

### 4.3 Performance (indicative)

| Mesure | runc | Kata Rust | Kata Go | Test |
|---|---|---|---|---|
| Pod prêt (médiane, 30 runs) | 0,65 s | 20,6 s | 30,9 s (p95 60,7 s) | PERF-01 |
| Pod prêt avec PVC | 2,1 s | 19,5 s | — | VOL-01 |
| Écriture séquentielle + sync sur PVC local | 323 MB/s | 32 MB/s | — | VOL-01 |
| Exec d'outil p50 / p95 | 61 / 75 ms | 237 / 318 ms | 287 / 489 ms | AGT-08 |
| Moteur dind privilégié prêt | quelques secondes | 99 à 164 s | 120 à 185 s | DIND-01 |
| Build multi-étapes (froid / chaud), dind en mémoire | — | 161–225 s / 64–88 s | 101–123 s / 16–34 s | DIND-05 V5 |
| CPU consommé sous limite 0,5 cœur | 0,50 | 0,50 | 0,50 | POL-15 |

En virtualisation imbriquée, chaque VM Kata est elle-même une VM dans une VM. Le facteur ×30 sur le démarrage ne doit **pas** être extrapolé : sur bare metal, l'ordre de grandeur publié est de 1 à 3 s. Le shim Go est plus lent et plus variable que le shim Rust sur ce poste.

### 4.4 Exploitation et policies d'admission

- **Kyverno s'applique à l'identique** aux pods runc et Kata : les 18 policies testées admettent et refusent les mêmes pods (POL-01 à POL-14, POL-18). Les contournements par Job, CronJob et conteneur éphémère sont bloqués dans les deux cas (POL-14).
- **Kata est imposable par policy** : une mutation force la RuntimeClass, l'overhead est bien ajouté, une autre RuntimeClass Kata est refusée (POL-12).
- **POL-11** (« privilégié seulement avec Kata ») fonctionne comme prévu : le pod privilégié est refusé en runc et admis en Kata. Cette policy est la condition d'usage du §6.
- **Écarts à l'exécution** : la limite CPU est respectée (POL-15) ; la limite `ephemeral-storage` ne l'est pas, faute d'éviction (POL-16) ; seccomp est absent (POL-17). La conformité à l'admission ne garantit donc pas la conformité à l'exécution en Kata.
- **Arrêt d'urgence** : un processus qui ignore SIGTERM est arrêté plus vite en Kata (la VM est détruite) que runc (AGT-20).

---

## 5. Comparaison des shims Rust et Go

| Point | Rust (`kata`) | Go (`kata-qemu`) |
|---|---|---|
| Isolation vers le nœud (SEC-04, SEC-09, DIND-14) | identique | identique |
| seccomp, `ephemeral-storage`, hostNetwork, hostPath | mêmes écarts | mêmes écarts |
| Échecs des variantes de build (DIND) | identiques : V1, V3, V4 en échec, V2 non supporté | identiques |
| Motif d'OOM (FUN-17) | **`Error`** | `OOMKilled` |
| Démarrage (PERF-01) | 20,6 s, stable | 30,9 s, très variable (p95 60,7 s) |
| Mémoire visible dans la VM (SEC-03) | 257 Mi | 2 230 Mi |
| Multiplication de processus (AGT-17) | bornée par une limite de PID de la VM (336) | exec bloqué sans limite constatée en 300 s (à analyser) |

Les écarts de sécurité ne dépendent pas du shim. Le choix du shim porte sur la supervision (motif d'OOM), le démarrage et le comportement sous saturation de processus.

---

## 6. Cas d'usage cibles

### 6.1 CI : construction d'images dans Kata (DIND)

**Verdict** : runc = **déconseillé** pour les builds privilégiés · Kata = **acceptable avec conditions**, pour la seule variante qui fonctionne

| Aspect | runc | Kata | Tests |
|---|---|---|---|
| Fonctionnel | 5 variantes sur 5 fonctionnent | dind privilégié avec stockage en mémoire (V5) seul fonctionnel ; dind privilégié sur disque (V1) et buildah (V3) échouent sur le montage overlay ; buildkit rootless (V4) ne démarre pas ; dind rootless (V2) non supporté | DIND-01, DIND-05, DIND-06 |
| Performance | référence | moteur prêt en ~2 min, build froid 100 à 225 s (indicatif) | DIND-01, DIND-05 |
| Sécurité | une étape malveillante d'un job dind privilégié monte le disque du nœud | elle ne voit que le disque de la VM | DIND-14 |

**Conditions de mise en œuvre** : policy « privilégié ⇒ Kata » (POL-11) sur les namespaces CI ; dind avec stockage en mémoire et taille de VM adaptée ; registre et secrets de push donnés par le pipeline, pas montés sur le nœud.

**Risques résiduels non couverts par Kata** : secrets de pipeline accessibles au code du build, egress du runner, administrateur du nœud.

### 6.2 Agents IA autonomes

**Verdict** : runc = **acceptable avec conditions** pour des outils relus · Kata = **recommandé** pour exécuter du code généré ou non relu

| Aspect | runc | Kata | Tests |
|---|---|---|---|
| Fonctionnel | référence | exec, API, arrêt d'urgence fonctionnent | AGT-08, AGT-14, AGT-20 |
| Performance | exec 61 ms | exec ~240 ms : acceptable pour un appel d'outil, pas pour des milliers d'appels courts | AGT-08 |
| Sécurité | un code qui obtient des privilèges atteint le nœud | il reste dans la VM | SEC-04, SEC-09 |
| Saturation de processus | bornée par la limite mémoire (conteneur tué en 2 s, aucune limite de PID) | Rust : bornée par la limite de PID de la VM ; Go : à analyser | AGT-17 |

**Ce que Kata apporte** : la frontière entre le code de l'agent et le nœud ou les autres pods.

**Ce qui relève d'autres contrôles** : l'injection de prompt, l'egress (destinations autorisées), les droits sur l'API (AGT-14 : pas de token, API refusée), les secrets donnés à l'agent, l'audit. Kata ne protège pas contre un agent qui abuse des droits qu'on lui a donnés.

### 6.3 Volumes et secrets

| Aspect | runc | Kata | Tests |
|---|---|---|---|
| Volumes | fonctionnels | fonctionnels (virtio-fs), écriture ~10× plus lente (indicatif) | VOL-01 |
| Isolation des volumes d'autres pods | atteints par un pod privilégié | non atteints | VOL-12 |
| Secrets : consommation, rotation | rotation en 2 s | rotation en ~85 s | SCR-01, SCR-02, SCR-03 |
| Vol de secrets d'autres pods | possible avec un hostPath kubelet | impossible depuis un pod Kata | SCR-05 |
| Secret lisible par l'administrateur du nœud | oui | oui | SCR-04 |

---

## 7. Matrice avantages, inconvénients et limites

| Modèle | Avantages | Inconvénients | Limites | Cas d'usage recommandés |
|---|---|---|---|---|
| runc | démarrage < 1 s (PERF-01) ; seccomp actif (SEC-08) ; OOM et éviction standard (FUN-17, POL-16) ; toutes les variantes de build (DIND-05) ; `hostNetwork` (FUN-30) | un pod privilégié ou avec hostPath compromet le nœud et les autres pods (SEC-04, SEC-09, VOL-12, SCR-05, DIND-14) | sécurité entièrement portée par l'admission et SELinux | charges standard, de confiance, sans privilège |
| Kata | pod privilégié contenu dans la VM (SEC-04, SEC-09, VOL-12, SCR-05, DIND-14) ; noyau séparé (SEC-01) ; vue limitée des ressources (SEC-03) ; même comportement Kyverno (POL-*) ; imposable par policy (POL-12) | démarrage ×30 et exec ×4 en imbriqué (PERF-01, AGT-08) ; overhead 250m / 320 Mi par pod (POL-12) ; pas de seccomp (SEC-08) ; pas d'éviction `ephemeral-storage` (POL-16) ; OOM mal qualifié en Rust (FUN-17) ; rotation des secrets lente (SCR-02) | `hostNetwork` non supporté et admis (FUN-30, POL-18) ; hostPath non privilégié refusé (SEC-05) ; 4 variantes de build sur 5 (DIND) ; ne protège pas le pod de l'hôte (SEC-18, SCR-04) | builds privilégiés, code non relu (agents IA), multi-tenant non fiable |

---

## 8. Recommandations d'usage

**Arbre de décision**

1. Le pod a-t-il besoin de privilèges (privileged, capacités larges, dind) ou exécute-t-il du code non relu ? **Non** → runc.
2. A-t-il besoin de `hostNetwork`, `hostPID`, de hostPath ou d'une éviction sur `ephemeral-storage` ? **Oui** → runc, et le privilège doit être justifié et revu (Kata ne le supporte pas ou ne l'applique pas).
3. Le démarrage doit-il prendre moins de 2 s (scale-out rapide, jobs très courts) ? **Oui** → runc, ou Kata avec un pool de pods préchauffés, à valider sur ENV-B.
4. Sinon → **Kata**, imposé par policy.

**Policies à déployer avec Kata**

- Mutation vers Kata pour les namespaces concernés, et refus de toute autre RuntimeClass (POL-12).
- « Privilégié seulement avec Kata » (POL-11).
- Refus de `hostNetwork` avec Kata (POL-18) : sans elle, un pod peut rendre le nœud indisponible.
- Interdiction des hostPath (POL-08), qui reste nécessaire même avec Kata.
- Quota d'`ephemeral-storage` au niveau du namespace et alerte sur l'usage disque, en compensation de POL-16.

**Supervision** : alerter sur le code de sortie 137, pas seulement sur le motif `OOMKilled` (FUN-17).

---

## 9. Risques, prérequis et coûts

| Sujet | Constat | Action |
|---|---|---|
| Matériel | Kata exige la virtualisation matérielle : nœuds bare metal ou instances qui exposent la virtualisation imbriquée | dédier un pool de nœuds Kata (label, taint) |
| Capacité | +250m CPU et +320 Mi par pod (overhead déclaré), plus la mémoire de la VM | dimensionner le pool, mesurer la densité sur ENV-B (PERF) |
| Support | kata-deploy upstream n'est pas supporté par Red Hat | cible : OpenShift Sandboxed Containers |
| Supervision | motif OOM différent (Rust), pas d'éviction disque | adapter les alertes |
| Compétences | diagnostic dans la VM (agent, virtio-fs, QEMU) | runbooks, formation de l'équipe plateforme |

---

## 10. Limites de l'étude

- **Virtualisation imbriquée** (VM Kata dans la VM CRC sur Mac) : toutes les mesures de temps et de débit Kata sont pessimistes.
- **Nœud unique** : pas de mesure inter-nœuds (réseau, migration), pas de densité multi-nœuds.
- **arm64** : la cible de production est x86_64 ; certains comportements (QEMU, noyau invité, appels système) peuvent différer.
- **kata-deploy upstream**, pas OpenShift Sandboxed Containers : la configuration du shim (seccomp notamment) peut changer avec OSC.
- **Agent Sandbox** absent du cluster : les tests AGT qui en dépendent n'ont pas été exécutés.
- **Échantillons** : 30 runs pour PERF-01, 3 à 5 pour les autres mesures, 1 à 2 pour les tests de sécurité (constats qualitatifs).
- **Incidents de campagne** :
  - mise en veille du Mac pendant la nuit : 21 tests rejoués ;
  - expiration des identifiants du composant réseau Multus de CRC : la campagne Go a été arrêtée puis reprise.
  Les runs affectés ont été rejoués, et seuls les runs rejoués sont comptés.
- **Kata Go et la version du banc** : les tests SEC-05 et SEC-18 du shim Go ont été exécutés avec une version antérieure du banc, sans la variante `spc_t` (SEC-05) et avec un défaut de repérage du processus marqué sur la vue nœud (SEC-18). Les verdicts entre pods ne sont pas affectés.
- **Volumes et secrets** : mesurés seulement avec le shim Rust et le backend local de CRC (pas de Ceph, NFS, Vault ni Conjur sur ENV-A).

---

## 11. Prochaines étapes

1. **ENV-B** : bare metal x86_64 avec OpenShift Sandboxed Containers. Remesurer la performance, vérifier seccomp, l'éviction et le motif d'OOM avec le shim supporté.
2. **Compléter le catalogue** : les 119 tests non automatisés (densité, réseau, IOPS, Jenkins et GitHub Actions de bout en bout, Agent Sandbox, Vault et Conjur).
3. **Analyser AGT-17 avec le shim Go** (exec bloqué sous saturation de processus) et les échecs de montage overlay des builds (DIND V1, V3).
4. **Pilote** : un namespace CI et un namespace d'agents IA sous policy « Kata obligatoire », avec la supervision adaptée.
5. **Hors de ce périmètre** : Confidential Containers (protection du pod contre l'hôte) et peer-pods.

---

## 12. Annexes

- **Catalogue complet et statuts** : [donnees.md](donnees.md) (généré depuis les résultats bruts).
- **Plan de tests** : [02-PLAN-DE-TESTS.md](../02-PLAN-DE-TESTS.md). **Format de retour** : [03-FORMAT-RAPPORT.md](../03-FORMAT-RAPPORT.md).
- **Versions exactes** : OpenShift 4.22.1, noyau du nœud 5.14.0-687.13.1.el9_8.aarch64, Kata 4.4.0 (kata-deploy), QEMU, noyau invité 6.18.62, Kyverno 1.20.0, CRI-O (voir `campaign.json` de chaque campagne).
- **Campagnes retenues** (une campagne plus récente remplace les runs d'un même test, d'une même variante et d'un même runtime) :

| Campagne | Contenu |
|---|---|
| `20261123-205546-ENV-A-a20e314` | campagne complète runc + Kata Rust |
| `20261124-081741-ENV-A-47fc568` | Kata Go, partie 1 (arrêtée par la panne Multus) |
| `20261124-104157-ENV-A-8a85ad9` | Kata Go, partie 2 et runs rejoués après la panne |
| `20261124-141740-ENV-A-8a85ad9` | VOL et SCR, runc + Kata Rust |
| `20261124-144102-ENV-A-8a85ad9` | SEC-04 à SEC-19, runc + Kata Rust |
| `20261124-145018-ENV-A-8a85ad9` | rejeu des 21 tests affectés par la mise en veille |
| `20261124-194458-ENV-A-cf3e9e3`, `…-202717-…-e77b665`, `…-202906-…-eaf9681` | rejeux après correction du banc (SCR-03, VOL-12, SEC-05, SEC-18) |

- **Reproduction** :

```sh
./precheck --context <contexte>
./run --context <contexte>                                        # mode sûr, runc + kata
./run --context <contexte> --kata-runtime-class kata-qemu --runtimes kata
uv run scripts/report.py --campaign <id> [--campaign <id> …] --site docs
```
