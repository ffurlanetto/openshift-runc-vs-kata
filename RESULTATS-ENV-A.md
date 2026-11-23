# Résultats ENV-A : OpenShift Local (CRC) arm64, virtualisation imbriquée

| | |
|---|---|
| Campagnes | `20261123-150324-ENV-A-2cfd032` (complète, 176 exécutions) + `20261123-160629-ENV-A-3996d56` (rejeu POL-14/15/17 après correction du banc) |
| Plateforme | OpenShift 4.22.1, 1 nœud arm64 (12 vCPU, 24 Go), CRI-O, SELinux enforcing |
| Kata | 4.4.0 via kata-deploy (pas OSC), runtime Rust `qemu-runtime-rs`, RuntimeClass `kata` (overhead 250m / 320Mi) |
| Kyverno | 1.20.0, policies CEL namespacées |
| Couverture | 23 tests automatisés sur 131 (FUN, PERF, SEC, POL) |

> **Portée** : virtualisation imbriquée sur Mac. Les mesures de performance Kata sont **indicatives** et pessimistes ; elles seront refaites sur ENV-B (x86_64 bare metal + OSC). Les constats fonctionnels et de sécurité sont, eux, représentatifs du comportement de Kata.

## Synthèse

| Test | runc | Kata | Lecture |
|---|---|---|---|
| SEC-01 Noyau partagé avec le nœud | oui (5.14 RHCOS) | **non** (6.18 invité) | L'isolation par VM est effective |
| SEC-03 Visibilité depuis le pod | 2 disques bloc, 16 nœuds /dev | 25 disques bloc (ceux de la VM), 15 nœuds /dev | Kata expose les périphériques de sa VM, pas ceux du nœud |
| PERF-01 Pod Ready (médiane, 30 runs) | **0,9 s** | **19,4 s** | ×22 en imbriqué (indicatif) |
| FUN-17 OOM (limite 128Mi) | `OOMKilled`, 1,3 s | tué (137) mais motif `Error`, 24 s | **PARTIAL** : la supervision basée sur `OOMKilled` ne voit rien en Kata |
| FUN-30 `hostNetwork` | fonctionne | **non supporté, et dangereux** | Voir constat 1 |
| POL-01 à POL-10 (bonnes pratiques Kyverno) | PASS | PASS | Policies identiques pour les deux runtimes, propagation 75–105 ms |
| POL-11 Privilégié seulement avec Kata | refusé | admis | PASS |
| POL-12 Kata imposé par mutation | PASS | PASS | Mutation + overhead appliqué ; autre RuntimeClass refusée |
| POL-13 Mode Audit + PolicyReport | PASS (13 s) | PASS (16 s) | |
| POL-14 Contournements (Job, CronJob, conteneur éphémère) | 0/3 admis | 0/3 admis | PASS |
| POL-15 Dépassement limite CPU (500m) | 0,50 cœur, voit 12 CPU | 0,50 cœur, voit 1 CPU | PASS : limite respectée ; Kata ne montre que ses vCPU |
| POL-16 Dépassement `ephemeral-storage` (100Mi, 300 MiB écrits) | **évincé** en 73 s | **non évincé** | **FAIL Kata** : voir constat 4 |
| POL-17 Privilèges effectifs | conformes | **seccomp absent** | **FAIL Kata** : voir constat 3 |
| POL-18 Pas de `hostNetwork` avec Kata | admis | refusé | PASS : garde-fou issu de FUN-30 |

## Constats à présenter au comité

1. **Un pod Kata en `hostNetwork` peut faire tomber le nœud.** Sur ENV-A, le premier pod de ce type a rendu le nœud injoignable (API server, SSH) ; il a fallu redémarrer la VM. Kata ne supporte pas `hostNetwork`, mais rien ne l'empêche à l'admission. **Mesure** : policy Kyverno `disallow-hostnetwork-kata` (POL-18), validée.
2. **La mémoire de la micro-VM est la limite mémoire du pod.** À 64Mi, le noyau invité ne démarre pas : le pod reste en `ContainerCreating` avec une erreur obscure (agent vsock injoignable). À 128Mi, il démarre. Un manifeste valide en runc peut donc ne jamais démarrer en Kata. **Mesure** : policy de limite mémoire minimale pour Kata, et documentation pour les équipes.
3. **Le profil seccomp n'est pas appliqué dans la VM.** `seccompProfile: RuntimeDefault` est accepté mais sans effet à l'intérieur de l'invité (`Seccomp: 0`). La frontière principale reste la VM ; c'est une couche de défense en moins à l'intérieur. À vérifier sur OSC (option `disable_guest_seccomp`).
4. **La limite `ephemeral-storage` n'a pas déclenché d'éviction en Kata.** Un pod limité à 100Mi a écrit 300 MiB sans être évincé, alors qu'il l'est en runc. Risque de saturation disque du nœud. À confirmer sur ENV-B avant d'en tirer une règle.
5. **Les OOM ne sont pas remontés comme tels.** Le conteneur est bien tué, mais Kubernetes affiche `Error` au lieu de `OOMKilled`. Alertes et tableaux de bord à adapter.
6. **Kata upstream sur OpenShift demande des adaptations SELinux** (labels des binaires, `virtiofsd --sandbox chroot`). OSC les apporte nativement : argument pour OSC en production (détail dans [01-ENVIRONNEMENT.md](01-ENVIRONNEMENT.md) §3.4).
7. **Kyverno fonctionne à l'identique pour les deux runtimes** : mêmes refus, mêmes délais, aucun contournement constaté. Il permet aussi d'**imposer** Kata (mutation) et de **réserver** les pods privilégiés à Kata.

## Incidents d'environnement (hors comparaison)

- Disque de la VM CRC rempli (54 Go) par le pod `downloads` de la console OpenShift, qui recopie les binaires `oc` à chaque redémarrage. Console retirée pendant les campagnes ; le precheck alerte désormais au-delà de 70 % de disque.

## Rejouer

```bash
./run --replay results/20261123-150324-ENV-A-2cfd032/campaign.json
```
