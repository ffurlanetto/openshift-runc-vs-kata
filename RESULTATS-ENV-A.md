# Résultats ENV-A : OpenShift Local (CRC) arm64, virtualisation imbriquée

| | |
|---|---|
| Rapport comité | [report/rapport-comite.md](report/rapport-comite.md) · site : <https://ffurlanetto.github.io/openshift-runc-vs-kata/> |
| Données détaillées | [report/donnees.md](report/donnees.md) (généré par `scripts/report.py`) |
| Plateforme | OpenShift 4.22.1, 1 nœud arm64 (12 vCPU, 24 Go), CRI-O, SELinux enforcing |
| Kata | 4.4.0 via kata-deploy (pas OSC) ; RuntimeClass `kata` (shim Rust `qemu-runtime-rs`) et `kata-qemu` (shim Go) ; overhead 250m / 320 Mi |
| Kyverno | 1.20.0 |
| Couverture | 44 tests automatisés sur 163, tous exécutés en runc, Kata Rust et Kata Go (VOL et SCR : runc et Kata Rust) |

> **Portée** : les mesures de performance Kata sont **indicatives** (virtualisation imbriquée) et seront refaites sur ENV-B (x86_64 bare metal + OSC). Les constats fonctionnels et de sécurité sont représentatifs du comportement de Kata.

## Synthèse

| Test | runc | Kata Rust | Kata Go | Lecture |
|---|---|---|---|---|
| SEC-01 Noyau partagé avec le nœud | oui | non (6.18 invité) | non | isolation par VM effective |
| SEC-04 Pod privilégié : évasion vers le nœud | 5 techniques réussies | 0 | 0 | Kata contient le pod privilégié |
| SEC-09 Pod privilégié : sysctl et module du nœud | modifiés (restaurés) | VM seulement | VM seulement | idem |
| VOL-12 Pod privilégié : volume d'un autre pod | atteint | non atteint | — | idem |
| SCR-05 Secrets des autres pods via hostPath kubelet | volés | aucun | — | idem |
| DIND-14 Étape CI malveillante : disque du nœud | monté | disque de la VM seulement | idem | idem |
| SEC-18 Voisin qui voit processus, mémoire, fichiers | non | non | non | isolation entre pods identique |
| SEC-18 / SCR-04 Administrateur du nœud : mémoire, fichiers, réseau, secrets du pod | lisibles | lisibles | lisibles | Kata ne protège pas le pod de l'hôte (rôle de CoCo) |
| SEC-19 Escalade setuid avec `allowPrivilegeEscalation: false` | bloquée | bloquée | bloquée | identique |
| SEC-08 / POL-17 Filtre seccomp dans le conteneur | actif | **absent** | **absent** | défense en profondeur perdue |
| SEC-05 hostPath, pod root non privilégié | accès si SELinux `spc_t`, refusé en `container_t` | pod non démarré | pod non démarré | à interdire à l'admission (POL-08) |
| POL-16 Éviction sur `ephemeral-storage` | oui (80 s) | **non** | **non** | compenser par quota |
| FUN-17 OOM (limite 128 Mi) | `OOMKilled`, 1,5 s | tué (137) mais motif **`Error`**, 26 s | `OOMKilled`, 55 s | supervision à adapter (Rust) |
| FUN-30 / POL-18 `hostNetwork` | fonctionne | non supporté, admis sans policy | idem | policy POL-18 obligatoire |
| PERF-01 Pod Ready (médiane, 30 runs) | 0,65 s | 20,6 s | 30,9 s | indicatif (imbriqué) |
| AGT-08 Exec d'outil p50 / p95 | 61 / 75 ms | 237 / 318 ms | 287 / 489 ms | indicatif |
| DIND-05 Build d'image : variantes fonctionnelles | 5/5 | 1/5 (dind privilégié, stockage en mémoire) | 1/5 | |
| POL-01..18 Policies Kyverno à l'admission | 18/18 | identiques | identiques | Kata imposable par mutation (POL-12) |

## Incidents de campagne

- Mise en veille du Mac (nuit du 23 au 24 novembre) : 21 tests rejoués, la détection de veille est désormais intégrée au banc.
- Identifiants expirés du démon Multus de CRC (24 novembre, environ 11 h 17) : plus de réseau pour les nouveaux pods ; pod Multus recréé, runs affectés rejoués.
- Défauts du banc corrigés après les essais : SCR-03, VOL-12, SEC-05, SEC-18, AGT-17, DIND-06, DIND-14.
