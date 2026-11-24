# Données : fiches de test générées

> Généré par `scripts/report.py` à partir des résultats bruts. Ne pas éditer à la main.

## Campagnes

| Campagne | Commit | Runtimes Kata | Exécutions | Début → fin |
|---|---|---|---|---|
| [`20261123-205546-ENV-A-a20e314`](../results/20261123-205546-ENV-A-a20e314/campaign.json) | `a20e314` | `kata` → `kata-qemu-runtime-rs` | 304 | 2026-11-23T20:55 → 2026-11-24T08:17 |
| [`20261124-081741-ENV-A-47fc568`](../results/20261124-081741-ENV-A-47fc568/campaign.json) | `47fc568` | `kata-qemu` → `kata-qemu` | ? | 2026-11-24T08:17 → ? |
| [`20261124-104157-ENV-A-8a85ad9`](../results/20261124-104157-ENV-A-8a85ad9/campaign.json) | `8a85ad9` | `kata-qemu` → `kata-qemu` | 136 | 2026-11-24T10:41 → 2026-11-24T14:17 |
| [`20261124-141740-ENV-A-8a85ad9`](../results/20261124-141740-ENV-A-8a85ad9/campaign.json) | `8a85ad9` | `kata` → `kata-qemu-runtime-rs` | 14 | 2026-11-24T14:17 → 2026-11-24T14:40 |
| [`20261124-144102-ENV-A-8a85ad9`](../results/20261124-144102-ENV-A-8a85ad9/campaign.json) | `8a85ad9` | `kata` → `kata-qemu-runtime-rs` | 12 | 2026-11-24T14:41 → 2026-11-24T14:49 |
| [`20261124-145018-ENV-A-8a85ad9`](../results/20261124-145018-ENV-A-8a85ad9/campaign.json) | `8a85ad9` | `kata` → `kata-qemu-runtime-rs` | 210 | 2026-11-24T14:50 → 2026-11-24T17:51 |
| [`20261124-194458-ENV-A-cf3e9e3`](../results/20261124-194458-ENV-A-cf3e9e3/campaign.json) | `cf3e9e3` | `kata` → `kata-qemu-runtime-rs` | 8 | 2026-11-24T19:44 → 2026-11-24T20:08 |
| [`20261124-202717-ENV-A-e77b665`](../results/20261124-202717-ENV-A-e77b665/campaign.json) | `e77b665` | `kata` → `kata-qemu-runtime-rs` | 2 | 2026-11-24T20:27 → 2026-11-24T20:28 |
| [`20261124-202906-ENV-A-eaf9681`](../results/20261124-202906-ENV-A-eaf9681/campaign.json) | `eaf9681` | `kata` → `kata-qemu-runtime-rs` | 2 | 2026-11-24T20:29 → 2026-11-24T20:36 |

## Tableau de bord : statuts par domaine

Nombre de tests (toutes variantes) dont le **pire** statut sur les runs mesurés est celui indiqué.

| Domaine | Tests | runc PASS / PARTIAL / FAIL / NON SUPP. / BLOQUÉ | kata:kata (rust) PASS / PARTIAL / FAIL / NON SUPP. / BLOQUÉ | kata:kata-qemu (go) PASS / PARTIAL / FAIL / NON SUPP. / BLOQUÉ |
|---|---|---|---|---|
| Fonctionnel | 2 | 2 / 0 / 0 / 0 / 0 | 0 / 1 / 0 / 1 / 0 | 1 / 0 / 0 / 1 / 0 |
| Performance | 1 | 1 / 0 / 0 / 0 / 0 | 1 / 0 / 0 / 0 / 0 | 1 / 0 / 0 / 0 / 0 |
| Sécurité | 8 | 8 / 0 / 0 / 0 / 0 | 6 / 1 / 1 / 0 / 0 | 6 / 1 / 1 / 0 / 0 |
| Policies d'admission (Kyverno) | 18 | 18 / 0 / 0 / 0 / 0 | 16 / 0 / 2 / 0 / 0 | 16 / 0 / 2 / 0 / 0 |
| CI dans Kata (DIND) | 4 | 15 / 0 / 0 / 0 / 0 | 4 / 0 / 5 / 6 / 0 | 5 / 0 / 6 / 4 / 0 |
| Agents IA | 4 | 4 / 0 / 0 / 0 / 0 | 4 / 0 / 0 / 0 / 0 | 3 / 0 / 1 / 0 / 0 |
| Volumes | 2 | 2 / 0 / 0 / 0 / 0 | 2 / 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 / 0 |
| Secrets | 5 | 5 / 0 / 0 / 0 / 0 | 5 / 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 / 0 |

## Fonctionnel

### FUN-17 — OOM : dépassement de limits.memory

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ⚠️ PARTIAL | ✅ PASS |
| `time_to_oom` | 1 467 ms <sub>p5–p95 779–1 789, n=5</sub> | 26 475 ms <sub>p5–p95 23 947–26 943, n=5</sub> ▼ +1705 % | 55 044 ms <sub>p5–p95 42 548–80 574, n=5</sub> ▼ +3652 % |

- *runc* : limite 128Mi ; terminated reason=OOMKilled exitCode=137

- *kata:kata (rust)* : limite 128Mi ; terminated reason=Error exitCode=137

- *kata:kata-qemu (go)* : limite 128Mi ; terminated reason=OOMKilled exitCode=137

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/FUN-17/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/FUN-17/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/FUN-17/kata)

### FUN-30 — hostNetwork

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ⛔ NON SUPPORTÉ | ⛔ NON SUPPORTÉ |
| `hostnetwork_kata_admitted` | — | 1 bool <sub>p5–p95 1–1, n=5</sub> | 1 bool <sub>p5–p95 1–1, n=5</sub> |
| `node_ip_visible` | 1 bool <sub>p5–p95 1–1, n=5</sub> | — | — |

- *runc* : IP du nœud ['192.0.2.0'] visibles dans le pod : ['192.0.2.0'] ; interfaces : ['0171f3bdb4f5b00', '0612ed70d769938', '0671566e5b43c5a', '0713ab799e65ccb', '095f9b7ee0133d9', '14a41e0d1120662', '185e6138e541c47', '1c26527d20a1132', '1f70afd755cb061', '203d790072738e4', '257d5a701e3cf7b', '280617d444b7bd6', '291b9ee773b98ab', '2a344990c650167', '2c8959838a15170', '32202b5f06a517f', '332fd82efbcedd4', '340ca22fd3d12ba', '34c57aa41ff01e3', '3552364668e3e83', '3dee8398d21aff1', '3ec93c40b8f4fff', '4719bdcd679a536', '4d261f734113307', '4f717478ff35d56', '50519d1d3fe8ed4', '55c3ff8abcdfda3', '5979a957

- *kata:kata (rust)* : pod Kata en hostNetwork ADMIS par le cluster : non exécuté (risque de perte du nœud, constaté sur ENV-A). Rejouer avec --allow-destructive sur un cluster jetable. \| NON SUPPORTÉ : hostNetwork non supporté par Kata et non bloqué à l'admission : un pod peut rendre le nœud indisponible (cf. POL-18)

- *kata:kata-qemu (go)* : pod Kata en hostNetwork ADMIS par le cluster : non exécuté (risque de perte du nœud, constaté sur ENV-A). Rejouer avec --allow-destructive sur un cluster jetable. \| NON SUPPORTÉ : hostNetwork non supporté par Kata et non bloqué à l'admission : un pod peut rendre le nœud indisponible (cf. POL-18)

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/FUN-30/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/FUN-30/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/FUN-30/kata)

## Performance

### PERF-01 — Latence de démarrage d'un pod

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `pod_ready_latency` | 645 ms <sub>p5–p95 452–1 489, n=30</sub> | 20 576 ms <sub>p5–p95 19 600–21 672, n=30</sub> ▼ +3090 % | 30 892 ms <sub>p5–p95 22 258–60 711, n=30</sub> ▼ +4689 % |
| `pod_ready_latency_server` | 1 s <sub>p5–p95 0–2, n=30</sub> | 20,5 s <sub>p5–p95 20–21,5, n=30</sub> ▼ +1950 % | 31 s <sub>p5–p95 21,8–60,1, n=30</sub> ▼ +3000 % |

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/PERF-01/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/PERF-01/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/PERF-01/kata)

## Sécurité

### SEC-01 — Identification du noyau vu par le pod

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `kernel_shared_with_node` | 1 bool <sub>p5–p95 1–1, n=5</sub> | 0 bool <sub>p5–p95 0–0, n=5</sub> | 0 bool <sub>p5–p95 0–0, n=5</sub> |

- *runc* : noyau pod=5.14.0-687.13.1.el9_8.aarch64 ; noyau nœud=5.14.0-687.13.1.el9_8.aarch64

- *kata:kata (rust)* : noyau pod=6.18.62 ; noyau nœud=5.14.0-687.13.1.el9_8.aarch64

- *kata:kata-qemu (go)* : noyau pod=6.18.62 ; noyau nœud=5.14.0-687.13.1.el9_8.aarch64

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/SEC-01/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/SEC-01/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/SEC-01/kata)

### SEC-03 — Visibilité du nœud depuis un pod restreint

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `visible_block_devices` | 2 count <sub>p5–p95 2–2, n=5</sub> | 25 count <sub>p5–p95 25–25, n=5</sub> ▼ +1150 % | 25 count <sub>p5–p95 25–25, n=5</sub> ▼ +1150 % |
| `visible_cpus` | 12 count <sub>p5–p95 12–12, n=5</sub> | 1 count <sub>p5–p95 1–1, n=5</sub> ▲ -92 % | 2 count <sub>p5–p95 2–2, n=5</sub> ▲ -83 % |
| `visible_dev_nodes` | 16 count <sub>p5–p95 16–16, n=5</sub> | 15 count <sub>p5–p95 15–15, n=5</sub> ▲ -6 % | 15 count <sub>p5–p95 15–15, n=5</sub> ▲ -6 % |
| `visible_memory` | 23 982 MiB <sub>p5–p95 23 982–23 982, n=5</sub> | 257 MiB <sub>p5–p95 257–257, n=5</sub> ▲ -99 % | 2 230 MiB <sub>p5–p95 2 230–2 230, n=5</sub> ▲ -91 % |
| `visible_mounts` | 28 count <sub>p5–p95 28–28, n=5</sub> | 24 count <sub>p5–p95 24–24, n=5</sub> ▲ -14 % | 24 count <sub>p5–p95 24–24, n=5</sub> ▲ -14 % |
| `visible_net_interfaces` | 2 count <sub>p5–p95 2–2, n=5</sub> | 2 count <sub>p5–p95 2–2, n=5</sub> ≈ +0 % | 2 count <sub>p5–p95 2–2, n=5</sub> ≈ +0 % |
| `visible_procs` | 5 count <sub>p5–p95 4,2–5, n=5</sub> | 4 count <sub>p5–p95 4–5, n=5</sub> ≈ -20 % (non significatif) | 5 count <sub>p5–p95 5–5, n=5</sub> ≈ +0 % |

- *runc* : mémoire visible 23982 MiB (nœud 23982 MiB), CPU visibles 12 (nœud 12)

- *kata:kata (rust)* : mémoire visible 257 MiB (nœud 23982 MiB), CPU visibles 1 (nœud 12)

- *kata:kata-qemu (go)* : mémoire visible 2230 MiB (nœud 23982 MiB), CPU visibles 2 (nœud 12)

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/SEC-03/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/SEC-03/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/SEC-03/kata)

### SEC-04 — Pod privilégié : évasion vers le nœud

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `node_escapes_priv` | 2 count | 0 count ≈ -100 % (non significatif) | 0 count <sub>p5–p95 0–0, n=2</sub> ≈ -100 % (non significatif) |
| `node_escapes_privpid` | 3 count | 0 count ≈ -100 % (non significatif) | 0 count <sub>p5–p95 0–0, n=2</sub> ≈ -100 % (non significatif) |
| `node_settings_not_restored` | 0 count | 0 count — | 0 count <sub>p5–p95 0–0, n=2</sub> — |

- *runc* : runc : 5 technique(s) ont atteint le nœud (témoin trouvé par la sonde runc) ; priv [nsenter=tenté, disk-loop0=lecture-seule, disk-vda2=lecture-seule, disk-vda3=monté-sans-var-tmp, disk-vda4=ÉVASION, release_agent=non-applicable, core_pattern=ÉVASION] ; privpid [nsenter=ÉVASION, disk-loop0=lecture-seule, disk-vda2=lecture-seule, disk-vda3=monté-sans-var-tmp, disk-vda4=ÉVASION, release_agent=non-applicable, core_pattern=ÉVASION] ; témoins restants après nettoyage : 0

- *kata:kata (rust)* : kata : 0 technique(s) ont atteint le nœud (témoin trouvé par la sonde runc) ; priv [nsenter=tenté, disk-vda1=lecture-seule, release_agent=non-applicable, core_pattern=tenté] ; privpid [nsenter=tenté, disk-vda1=lecture-seule, release_agent=non-applicable, core_pattern=tenté] ; témoins restants après nettoyage : 0

- *kata:kata-qemu (go)* : kata : 0 technique(s) ont atteint le nœud (témoin trouvé par la sonde runc) ; priv [nsenter=tenté, disk-vda1=lecture-seule, release_agent=non-applicable, core_pattern=tenté] ; privpid [nsenter=tenté, disk-vda1=lecture-seule, release_agent=non-applicable, core_pattern=tenté] ; témoins restants après nettoyage : 0

Résultats bruts : [runc](../results/20261124-144102-ENV-A-8a85ad9/ENV-A/SEC-04/runc) · [kata:kata (rust)](../results/20261124-144102-ENV-A-8a85ad9/ENV-A/SEC-04/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/SEC-04/kata)

### SEC-05 — hostPath : accès au nœud malgré Kata ?

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ❌ FAIL | ❌ FAIL |
| `hostpath_access_default_selinux` | 0 bool | 0 bool | — |
| `hostpath_default_selinux_pod_started` | 1 bool | 0 bool | — |
| `hostpath_read` | 1 bool | 0 bool | — |
| `hostpath_write_seen_on_node` | 1 bool | 0 bool | — |
| `node_sensitive_files_readable` | 2 count | 0 count ≈ -100 % (non significatif) | — |

- *runc* : runc : hostPath avec spc_t : lu=oui, écriture vue par le nœud=oui (propriétaire côté nœud 0:0) ; avec le SELinux par défaut (system_u:system_r:container_t:s0:c34,c59) : lu=non, écrit=non ; type de montage xfs ; racine du nœud en lecture seule : fichiers sensibles lisibles ['shadow', 'kubelet.conf'], écriture refusée=NON ; résidus : 0

- *kata:kata (rust)* : kata : hostPath avec spc_t : lu=non, écriture vue par le nœud=non (propriétaire côté nœud -, pod non démarré) ; avec le SELinux par défaut (?) : pod non démarré ; type de montage ? ; pod hostPath « / » non démarré : kubectl wait pod/hostroot --for=condition=Ready --timeout=150s -n kvr-84e5e-sec-05-kata-1 -> rc=1 : error: timed out waiting for the condition on pods/hostroot ; résidus : 0

- *kata:kata-qemu (go)* : ERREUR : OcError: kubectl wait pod/hostpath --for=condition=Ready --timeout=240s -n kvr-a5b1b-sec-05-kata-1 -> rc=1 : error: timed out waiting for the condition on pods/hostpath

- *kata:kata-qemu (go)* : ERREUR : OcError: kubectl wait pod/hostpath --for=condition=Ready --timeout=240s -n kvr-a5b1b-sec-05-kata-2 -> rc=1 : error: timed out waiting for the condition on pods/hostpath

Résultats bruts : [runc](../results/20261124-202906-ENV-A-eaf9681/ENV-A/SEC-05/runc) · [kata:kata (rust)](../results/20261124-202906-ENV-A-eaf9681/ENV-A/SEC-05/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/SEC-05/kata)

### SEC-08 — Surface noyau atteignable depuis un pod restreint

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ⚠️ PARTIAL | ⚠️ PARTIAL |
| `seccomp_filter_active` | 1 bool | 0 bool | 0 bool <sub>p5–p95 0–0, n=2</sub> |
| `syscalls_blocked` | 15 count | 7 count ≈ -53 % (non significatif) | 7 count <sub>p5–p95 7–7, n=2</sub> ≈ -53 % (non significatif) |
| `syscalls_reached` | 3 count | 11 count ≈ +267 % (non significatif) | 11 count <sub>p5–p95 11–11, n=2</sub> ≈ +267 % (non significatif) |

- *runc* : runc : seccomp=2 (filtre actif), NoNewPrivs=1, uid=1001, noyau 5.14.0-687.13.1.el9_8.aarch64 (du NŒUD) ; 3/18 appels atteignent le noyau du NŒUD : keyctl(succès), ptrace(succès), setns(EBADF) ; bloqués : add_key, bpf, chroot, clock_settime, init_module, io_uring_setup, kexec_load, mount, open_by_handle_at, perf_event_open, pivot_root, swapon, syslog, unshare, userfaultfd

- *kata:kata (rust)* : kata : seccomp=0 (AUCUN filtre), NoNewPrivs=1, uid=1001, noyau 6.18.62 (de la VM) ; 11/18 appels atteignent le noyau de la VM : add_key(succès), bpf(EINVAL), clock_settime(EINVAL), io_uring_setup(succès), keyctl(succès), open_by_handle_at(EFAULT), perf_event_open(EFAULT), ptrace(succès), setns(EBADF), syslog(succès), unshare(succès) ; bloqués : chroot, init_module, kexec_load, mount, pivot_root, swapon, userfaultfd

- *kata:kata-qemu (go)* : kata : seccomp=0 (AUCUN filtre), NoNewPrivs=1, uid=1001, noyau 6.18.62 (de la VM) ; 11/18 appels atteignent le noyau de la VM : add_key(succès), bpf(EINVAL), clock_settime(EINVAL), io_uring_setup(succès), keyctl(succès), open_by_handle_at(EFAULT), perf_event_open(EFAULT), ptrace(succès), setns(EBADF), syslog(succès), unshare(succès) ; bloqués : chroot, init_module, kexec_load, mount, pivot_root, swapon, userfaultfd

Résultats bruts : [runc](../results/20261124-144102-ENV-A-8a85ad9/ENV-A/SEC-08/runc) · [kata:kata (rust)](../results/20261124-144102-ENV-A-8a85ad9/ENV-A/SEC-08/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/SEC-08/kata)

### SEC-09 — Pod privilégié : sysctl et module noyau du nœud

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `node_left_modified` | 0 bool | 0 bool | 0 bool <sub>p5–p95 0–0, n=2</sub> |
| `node_module_loaded` | 1 bool | 0 bool | 0 bool <sub>p5–p95 0–0, n=2</sub> |
| `node_sysctl_modified` | 1 bool | 0 bool | 0 bool <sub>p5–p95 0–0, n=2</sub> |

- *runc* : runc : sysctl écrit dans le pod=oui, vu sur le NŒUD=OUI (restauré=oui) ; module tcp_htcp : chargé (noyau du pod 5.14.0-687.13.1.el9_8.aarch64, nœud 5.14.0-687.13.1.el9_8.aarch64), chargé sur le NŒUD=OUI, déchargé ; nœud remis en l'état=oui

- *kata:kata (rust)* : kata : sysctl écrit dans le pod=oui, vu sur le NŒUD=non (restauré=oui) ; module tcp_htcp : refusé (Function not implemented) (noyau du pod 6.18.62, nœud 5.14.0-687.13.1.el9_8.aarch64), chargé sur le NŒUD=non ; nœud remis en l'état=oui

- *kata:kata-qemu (go)* : kata : sysctl écrit dans le pod=oui, vu sur le NŒUD=non (restauré=oui) ; module tcp_htcp : refusé (Function not implemented) (noyau du pod 6.18.62, nœud 5.14.0-687.13.1.el9_8.aarch64), chargé sur le NŒUD=non ; nœud remis en l'état=oui

Résultats bruts : [runc](../results/20261124-144102-ENV-A-8a85ad9/ENV-A/SEC-09/runc) · [kata:kata (rust)](../results/20261124-144102-ENV-A-8a85ad9/ENV-A/SEC-09/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/SEC-09/kata)

### SEC-18 — Isolation entre pods : processus, mémoire, fichiers, réseau

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `node_captures_network` | 1 bool | 1 bool | 1 bool <sub>p5–p95 1–1, n=2</sub> |
| `node_reads_files` | 1 bool | 1 bool | 1 bool <sub>p5–p95 1–1, n=2</sub> |
| `node_reads_memory` | 1 bool | 1 bool | 1 bool <sub>p5–p95 1–1, n=2</sub> |
| `node_sees_process` | 1 bool | 0 bool | 0 bool <sub>p5–p95 0–0, n=2</sub> |
| `peer_visibility_leaks` | 0 count | 0 count — | 0 count <sub>p5–p95 0–0, n=2</sub> — |

- *runc* : runc : voisins (voisin runc) : AUCUNE visibilité (processus visibles par le voisin runc : 2) ; administrateur du nœud : processus marqué VISIBLE (processus du pod vus sur le nœud : bash, conmon, sleep), mémoire LUE, fichier TROUVÉ, réseau CAPTURÉ

- *kata:kata (rust)* : kata : voisins (voisin runc, voisin kata) : AUCUNE visibilité (processus visibles par le voisin runc : 2) ; administrateur du nœud : processus marqué invisible (processus du pod vus sur le nœud : containerd-shim, qemu-system-aar, vhost-530063, virtiofsd), mémoire LUE, fichier TROUVÉ, réseau CAPTURÉ

- *kata:kata-qemu (go)* : kata : voisins (voisin runc, voisin kata) : AUCUNE visibilité (processus visibles par le voisin runc : 2) ; administrateur du nœud : processus marqué invisible (processus du pod vus sur le nœud : qemu-system-aar), mémoire LUE, fichier TROUVÉ, réseau CAPTURÉ

Résultats bruts : [runc](../results/20261124-202717-ENV-A-e77b665/ENV-A/SEC-18/runc) · [kata:kata (rust)](../results/20261124-202717-ENV-A-e77b665/ENV-A/SEC-18/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/SEC-18/kata)

### SEC-19 — Escalade de privilèges dans le pod (setuid, capacités, no_new_privs)

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `restricted_caps_effective` | 0 count | 0 count — | 0 count <sub>p5–p95 0–0, n=2</sub> — |
| `root_caps_effective` | 9 count | 9 count ≈ +0 % | 9 count <sub>p5–p95 9–9, n=2</sub> ≈ +0 % |
| `setuid_escalation_blocked_by_nnp` | 1 bool | 1 bool | 1 bool <sub>p5–p95 1–1, n=2</sub> |
| `setuid_escalation_when_allowed` | 0 bool | 0 bool | 0 bool <sub>p5–p95 0–0, n=2</sub> |

- *runc* : runc : restreint NNP=1 seccomp=2 capacités=aucune userns=unshare: unshare failed: Function not implemented ; setuid-root lancé par 1001 → euid 1001 avec allowPrivilegeEscalation=false, 1001 avec true (fs overlayfs 0) ; root : 9 capacités (chown, dac_override, fowner, fsetid, kill, setgid, setuid, setpcap, net_bind_service), utilisables : chown ; uid_map 0 0 4294967295

- *kata:kata (rust)* : kata : restreint NNP=1 seccomp=0 capacités=aucune userns=uid=0 capeff=000001ffffffffff ; setuid-root lancé par 1001 → euid 1001 avec allowPrivilegeEscalation=false, 1001 avec true (fs fuseblk 0) ; root : 9 capacités (chown, dac_override, fowner, fsetid, kill, setgid, setuid, setpcap, net_bind_service), utilisables : chown ; uid_map 0 0 4294967295

- *kata:kata-qemu (go)* : kata : restreint NNP=1 seccomp=0 capacités=aucune userns=uid=0 capeff=000001ffffffffff ; setuid-root lancé par 1001 → euid 1001 avec allowPrivilegeEscalation=false, 1001 avec true (fs fuseblk 0) ; root : 9 capacités (chown, dac_override, fowner, fsetid, kill, setgid, setuid, setpcap, net_bind_service), utilisables : chown ; uid_map 0 0 4294967295

Résultats bruts : [runc](../results/20261124-144102-ENV-A-8a85ad9/ENV-A/SEC-19/runc) · [kata:kata (rust)](../results/20261124-144102-ENV-A-8a85ad9/ENV-A/SEC-19/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/SEC-19/kata)

## Policies d'admission (Kyverno)

### POL-01 — Kyverno : non-root obligatoire

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `compliant_admitted_enforce` | 1 bool | 1 bool | 1 bool |
| `policy_propagation` | 80 ms | 85 ms ≈ +6 % (non significatif) | 84 ms ≈ +5 % |
| `violating_admitted_enforce` | 0 bool | 0 bool | 0 bool |
| `violating_admitted_without_policy` | 1 bool | 1 bool | 1 bool |
| `violating_deployment_admitted_enforce` | 0 bool | 0 bool | 0 bool |

- *runc* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata (rust)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata-qemu (go)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-01/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-01/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-01/kata)

### POL-02 — Kyverno : requests et limits obligatoires

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `compliant_admitted_enforce` | 1 bool | 1 bool | 1 bool |
| `policy_propagation` | 77 ms | 69 ms ≈ -10 % (non significatif) | 92 ms ≈ +19 % (non significatif) |
| `violating_admitted_enforce` | 0 bool | 0 bool | 0 bool |
| `violating_admitted_without_policy` | 1 bool | 1 bool | 1 bool |
| `violating_deployment_admitted_enforce` | 0 bool | 0 bool | 0 bool |

- *runc* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata (rust)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata-qemu (go)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-02/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-02/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-02/kata)

### POL-03 — Kyverno : plafond des limits

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `compliant_admitted_enforce` | 1 bool | 1 bool | 1 bool |
| `policy_propagation` | 78 ms | 74 ms ≈ -5 % (non significatif) | 84 ms ≈ +8 % (non significatif) |
| `violating_admitted_enforce` | 0 bool | 0 bool | 0 bool |
| `violating_admitted_without_policy` | 1 bool | 1 bool | 1 bool |
| `violating_deployment_admitted_enforce` | 0 bool | 0 bool | 0 bool |

- *runc* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata (rust)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata-qemu (go)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-03/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-03/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-03/kata)

### POL-04 — Kyverno : conteneurs privilégiés interdits

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `compliant_admitted_enforce` | 1 bool | 1 bool | 1 bool |
| `policy_propagation` | 72 ms | 81 ms ≈ +12 % (non significatif) | 83 ms ≈ +15 % (non significatif) |
| `violating_admitted_enforce` | 0 bool | 0 bool | 0 bool |
| `violating_admitted_without_policy` | 1 bool | 1 bool | 1 bool |
| `violating_deployment_admitted_enforce` | 0 bool | 0 bool | 0 bool |

- *runc* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata (rust)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata-qemu (go)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-04/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-04/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-04/kata)

### POL-05 — Kyverno : escalade de privilèges interdite

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `compliant_admitted_enforce` | 1 bool | 1 bool | 1 bool |
| `policy_propagation` | 72 ms | 96 ms ≈ +33 % (non significatif) | 79 ms ≈ +10 % (non significatif) |
| `violating_admitted_enforce` | 0 bool | 0 bool | 0 bool |
| `violating_admitted_without_policy` | 1 bool | 1 bool | 1 bool |
| `violating_deployment_admitted_enforce` | 0 bool | 0 bool | 0 bool |

- *runc* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata (rust)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata-qemu (go)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-05/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-05/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-05/kata)

### POL-06 — Kyverno : capabilities restreintes

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `compliant_admitted_enforce` | 1 bool | 1 bool | 1 bool |
| `policy_propagation` | 83 ms | 76 ms ≈ -8 % (non significatif) | 76 ms ≈ -8 % (non significatif) |
| `violating_admitted_enforce` | 0 bool | 0 bool | 0 bool |
| `violating_admitted_without_policy` | 1 bool | 1 bool | 1 bool |
| `violating_deployment_admitted_enforce` | 0 bool | 0 bool | 0 bool |

- *runc* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata (rust)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata-qemu (go)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-06/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-06/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-06/kata)

### POL-07 — Kyverno : namespaces de l'hôte interdits

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `compliant_admitted_enforce` | 1 bool | 1 bool | 1 bool |
| `policy_propagation` | 79 ms | 83 ms ≈ +5 % (non significatif) | 148 ms ≈ +87 % (non significatif) |
| `violating_admitted_enforce` | 0 bool | 0 bool | 0 bool |
| `violating_admitted_without_policy` | 1 bool | 1 bool | 1 bool |
| `violating_deployment_admitted_enforce` | 0 bool | 0 bool | 0 bool |

- *runc* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata (rust)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata-qemu (go)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-07/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-07/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-07/kata)

### POL-08 — Kyverno : hostPath interdit

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `compliant_admitted_enforce` | 1 bool | 1 bool | 1 bool |
| `policy_propagation` | 74 ms | 76 ms ≈ +3 % | 76 ms ≈ +3 % |
| `violating_admitted_enforce` | 0 bool | 0 bool | 0 bool |
| `violating_admitted_without_policy` | 1 bool | 1 bool | 1 bool |
| `violating_deployment_admitted_enforce` | 0 bool | 0 bool | 0 bool |

- *runc* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata (rust)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata-qemu (go)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-08/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-08/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-08/kata)

### POL-09 — Kyverno : seccomp RuntimeDefault obligatoire

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `compliant_admitted_enforce` | 1 bool | 1 bool | 1 bool |
| `policy_propagation` | 72 ms | 73 ms ≈ +1 % | 210 ms ≈ +192 % (non significatif) |
| `violating_admitted_enforce` | 0 bool | 0 bool | 0 bool |
| `violating_admitted_without_policy` | 1 bool | 1 bool | 1 bool |
| `violating_deployment_admitted_enforce` | 0 bool | 0 bool | 0 bool |

- *runc* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata (rust)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata-qemu (go)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-09/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-09/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-09/kata)

### POL-10 — Kyverno : images par digest obligatoires

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `compliant_admitted_enforce` | 1 bool | 1 bool | 1 bool |
| `policy_propagation` | 71 ms | 76 ms ≈ +7 % (non significatif) | 83 ms ≈ +17 % (non significatif) |
| `violating_admitted_enforce` | 0 bool | 0 bool | 0 bool |
| `violating_admitted_without_policy` | 1 bool | 1 bool | 1 bool |
| `violating_deployment_admitted_enforce` | 0 bool | 0 bool | 0 bool |

- *runc* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata (rust)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

- *kata:kata-qemu (go)* : Kyverno v1.20.0 (cel) ; Enforce : conforme admis, non conforme refusé, Deployment non conforme refusé

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-10/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-10/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-10/kata)

### POL-11 — Kyverno : privilégié seulement avec Kata

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `policy_propagation` | 84 ms | — | — |
| `privileged_admitted` | 0 bool | 1 bool | 1 bool |
| `unprivileged_admitted` | 1 bool | 1 bool | 1 bool |

- *runc* : runc : pod privilégié refusé

- *kata:kata (rust)* : kata : pod privilégié ADMIS

- *kata:kata-qemu (go)* : kata : pod privilégié ADMIS

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-11/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-11/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-11/kata)

### POL-12 — Kyverno : forcer Kata (mutation + validation)

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `mutated_to_kata` | 1 bool | 1 bool | 1 bool |
| `other_runtime_class_admitted` | 0 bool | 0 bool | 0 bool |
| `overhead_set_after_mutation` | 1 bool | 1 bool | 1 bool |

- *runc* : muté vers kata=True ; overhead après mutation={'cpu': '250m', 'memory': '320Mi'} (RuntimeClass : {'podFixed': {'cpu': '250m', 'memory': '320Mi'}}) ; autre RuntimeClass kata-qemu admise=False

- *kata:kata (rust)* : muté vers kata=True ; overhead après mutation={'cpu': '250m', 'memory': '320Mi'} (RuntimeClass : {'podFixed': {'cpu': '250m', 'memory': '320Mi'}}) ; autre RuntimeClass kata-qemu admise=False

- *kata:kata-qemu (go)* : muté vers kata-qemu=True ; overhead après mutation={'cpu': '250m', 'memory': '320Mi'} (RuntimeClass : {'podFixed': {'cpu': '250m', 'memory': '320Mi'}}) ; autre RuntimeClass kata admise=False

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-12/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-12/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-12/kata)

### POL-13 — Kyverno : mode Audit (admission + rapport)

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `report_delay` | 12,9 s | 16 s ≈ +24 % (non significatif) | 12,9 s ≈ +0 % |
| `reported_in_policy_report` | 1 bool | 1 bool | 1 bool |
| `violating_admitted_audit` | 1 bool | 1 bool | 1 bool |

- *runc* : Audit : pod non conforme admis=True, avertissement client=True, rapport=oui (policyreports.wgpolicyk8s.io)

- *kata:kata (rust)* : Audit : pod non conforme admis=True, avertissement client=True, rapport=oui (policyreports.wgpolicyk8s.io)

- *kata:kata-qemu (go)* : Audit : pod non conforme admis=True, avertissement client=True, rapport=oui (policyreports.wgpolicyk8s.io)

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-13/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-13/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-13/kata)

### POL-14 — Kyverno : contournements (Job, CronJob, conteneur éphémère)

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `bypass_cronjob_admitted` | 0 bool | 0 bool | 0 bool |
| `bypass_ephemeralcontainer_admitted` | 0 bool | 0 bool | 0 bool |
| `bypass_job_admitted` | 0 bool | 0 bool | 0 bool |

- *runc* : vecteurs admis malgré Enforce : aucun

- *kata:kata (rust)* : vecteurs admis malgré Enforce : aucun

- *kata:kata-qemu (go)* : vecteurs admis malgré Enforce : aucun

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-14/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-14/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-14/kata)

### POL-15 — Dépassement de la limite CPU à l'exécution

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `cpu_limit_ratio` | 1,01 ratio <sub>p5–p95 1,01–1,01, n=3</sub> | 1 ratio <sub>p5–p95 1–1, n=3</sub> ≈ -1 % | 1,01 ratio <sub>p5–p95 0,996–1,03, n=3</sub> ≈ -0 % |
| `effective_cpu_cores` | 0,504 cores <sub>p5–p95 0,503–0,504, n=3</sub> | 0,501 cores <sub>p5–p95 0,501–0,502, n=3</sub> ≈ -1 % | 0,503 cores <sub>p5–p95 0,498–0,515, n=3</sub> ≈ -0 % |
| `visible_cpus` | 12 count <sub>p5–p95 12–12, n=3</sub> | 1 count <sub>p5–p95 1–1, n=3</sub> ▲ -92 % | 2 count <sub>p5–p95 2–2, n=3</sub> ▲ -83 % |

- *runc* : limite 0.5 cœur(s), consommé 0.50 ; cpu.max=50000 ; nproc=12

- *kata:kata (rust)* : limite 0.5 cœur(s), consommé 0.50 ; cpu.max=50000 ; nproc=1

- *kata:kata-qemu (go)* : limite 0.5 cœur(s), consommé 0.50 ; cpu.max=50000 ; nproc=2

- *kata:kata-qemu (go)* : limite 0.5 cœur(s), consommé 0.52 ; cpu.max=50000 ; nproc=2

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-15/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/POL-15/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-15/kata)

### POL-16 — Dépassement de la limite ephemeral-storage

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ❌ FAIL | ❌ FAIL |
| `evicted` | 1 bool | 0 bool | 0 bool |
| `time_to_eviction` | 79,6 s | — | — |

- *runc* : écrit 300 MiB pour une limite 100Mi : phase=Failed reason=Evicted

- *kata:kata (rust)* : écrit 300 MiB pour une limite 100Mi : phase=Running reason=None

- *kata:kata-qemu (go)* : écrit 300 MiB pour une limite 100Mi : phase=Running reason=None

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/POL-16/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/POL-16/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-16/kata)

### POL-17 — Privilèges effectifs d'un pod conforme

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ❌ FAIL | ❌ FAIL |
| `etc_read_only` | 1 bool | 1 bool | 1 bool |
| `no_effective_caps` | 1 bool | 1 bool | 1 bool |
| `no_new_privs` | 1 bool | 1 bool | 1 bool |
| `seccomp_filter` | 1 bool | 0 bool | 0 bool |
| `uid_non_root` | 1 bool | 1 bool | 1 bool |

- *runc* : {'uid': '1002630000', 'CapPrm': '0000000000000000', 'CapEff': '0000000000000000', 'NoNewPrivs': '1', 'Seccomp': '2', 'etc_writable': '0'} ; écarts : aucun

- *kata:kata (rust)* : {'uid': '1002640000', 'CapPrm': '0000000000000000', 'CapEff': '0000000000000000', 'NoNewPrivs': '1', 'Seccomp': '0', 'etc_writable': '0'} ; écarts : ['seccomp_filter']

- *kata:kata-qemu (go)* : {'uid': '1004450000', 'CapPrm': '0000000000000000', 'CapEff': '0000000000000000', 'NoNewPrivs': '1', 'Seccomp': '0', 'etc_writable': '0'} ; écarts : ['seccomp_filter']

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/POL-17/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/POL-17/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-17/kata)

### POL-18 — Kyverno : pas de hostNetwork avec Kata

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `hostnetwork_admitted_with_policy` | 1 bool | 0 bool | 0 bool |
| `hostnetwork_admitted_without_policy` | 1 bool | 1 bool | 1 bool |
| `policy_propagation` | 261 ms | 97 ms ≈ -63 % (non significatif) | 227 ms ≈ -13 % (non significatif) |

- *runc* : runc : pod hostNetwork ADMIS avec la policy

- *kata:kata (rust)* : kata : pod hostNetwork refusé avec la policy

- *kata:kata-qemu (go)* : kata : pod hostNetwork refusé avec la policy

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/POL-18/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/POL-18/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/POL-18/kata)

## CI dans Kata (DIND)

### DIND-01 — Démarrage du moteur de build

**Variante `V1-dind-privileged`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `engine_ready_after_pod` | 16,9 s <sub>p5–p95 16,9–16,9, n=3</sub> | 70,1 s <sub>p5–p95 66,2–116, n=3</sub> ▼ +315 % | 73,4 s <sub>p5–p95 66–77,5, n=3</sub> ▼ +334 % |
| `engine_ready_total` | 18,5 s <sub>p5–p95 18,2–18,8, n=3</sub> | 101 s <sub>p5–p95 99,4–158, n=3</sub> ▼ +448 % | 176 s <sub>p5–p95 126–184, n=3</sub> ▼ +853 % |
| `pod_ready` | 1,6 s <sub>p5–p95 1,33–1,87, n=3</sub> | 33,4 s <sub>p5–p95 31,5–41,4, n=3</sub> ▼ +1987 % | 111 s <sub>p5–p95 48,7–111, n=3</sub> ▼ +6838 % |

- *runc* : V1-dind-privileged : moteur prêt en 18.8s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *runc* : V1-dind-privileged : moteur prêt en 18.5s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *runc* : V1-dind-privileged : moteur prêt en 18.2s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *kata:kata (rust)* : V1-dind-privileged : moteur prêt en 99.2s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *kata:kata (rust)* : V1-dind-privileged : moteur prêt en 163.9s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *kata:kata (rust)* : V1-dind-privileged : moteur prêt en 101.4s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *kata:kata-qemu (go)* : V1-dind-privileged : moteur prêt en 184.7s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *kata:kata-qemu (go)* : V1-dind-privileged : moteur prêt en 176.3s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *kata:kata-qemu (go)* : V1-dind-privileged : moteur prêt en 119.9s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/DIND-01/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/DIND-01/kata) · [kata:kata-qemu (go)](../results/20261124-081741-ENV-A-47fc568/ENV-A/DIND-01/kata)

**Variante `V2-dind-rootless`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ⛔ NON SUPPORTÉ | ⛔ NON SUPPORTÉ |
| `engine_ready_after_pod` | 16,8 s <sub>p5–p95 16,8–16,9, n=3</sub> | — | — |
| `engine_ready_total` | 18,4 s <sub>p5–p95 18,4–18,7, n=3</sub> | — | — |
| `pod_ready` | 1,5 s <sub>p5–p95 1,5–1,86, n=3</sub> | — | — |

- *runc* : V2-dind-rootless : moteur prêt en 18.7s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=rootless name=cgroupns]

- *runc* : V2-dind-rootless : moteur prêt en 18.4s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=rootless name=cgroupns]

- *kata:kata (rust)* : NON SUPPORTÉ : moteur V2-dind-rootless indisponible après 180s : error: cannot exec into a container in a completed pod; current phase is Failed

- *kata:kata-qemu (go)* : NON SUPPORTÉ : moteur V2-dind-rootless indisponible après 300s : error: cannot exec into a container in a completed pod; current phase is Failed

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/DIND-01/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/DIND-01/kata) · [kata:kata-qemu (go)](../results/20261124-081741-ENV-A-47fc568/ENV-A/DIND-01/kata)

**Variante `V3-buildah`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `engine_ready_after_pod` | 0,1 s <sub>p5–p95 0,1–0,1, n=3</sub> | 10,1 s <sub>p5–p95 9,11–10,2, n=3</sub> ▼ +10000 % | 8,1 s <sub>p5–p95 6,75–8,82, n=3</sub> ▼ +8000 % |
| `engine_ready_total` | 1,5 s <sub>p5–p95 1,41–1,5, n=3</sub> | 47,6 s <sub>p5–p95 34,6–54,9, n=3</sub> ▼ +3073 % | 116 s <sub>p5–p95 116–121, n=3</sub> ▼ +7640 % |
| `pod_ready` | 1,4 s <sub>p5–p95 1,31–1,4, n=3</sub> | 37,5 s <sub>p5–p95 25,5–44,8, n=3</sub> ▼ +2579 % | 109 s <sub>p5–p95 107–113, n=3</sub> ▼ +7707 % |

- *runc* : V3-buildah : moteur prêt en 1.4s ; engine_version=1.46.1, storage_driver=overlay

- *runc* : V3-buildah : moteur prêt en 1.5s ; engine_version=1.46.1, storage_driver=overlay

- *kata:kata (rust)* : V3-buildah : moteur prêt en 47.6s ; engine_version=1.46.1, storage_driver=overlay

- *kata:kata (rust)* : V3-buildah : moteur prêt en 33.2s ; engine_version=1.46.1, storage_driver=overlay

- *kata:kata (rust)* : V3-buildah : moteur prêt en 55.7s ; engine_version=1.46.1, storage_driver=overlay

- *kata:kata-qemu (go)* : V3-buildah : moteur prêt en 115.9s ; engine_version=1.46.1, storage_driver=overlay

- *kata:kata-qemu (go)* : V3-buildah : moteur prêt en 116.1s ; engine_version=1.46.1, storage_driver=overlay

- *kata:kata-qemu (go)* : V3-buildah : moteur prêt en 121.4s ; engine_version=1.46.1, storage_driver=overlay

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/DIND-01/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/DIND-01/kata) · [kata:kata-qemu (go)](../results/20261124-081741-ENV-A-47fc568/ENV-A/DIND-01/kata)

**Variante `V4-buildkit-rootless`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ❌ FAIL | ❌ FAIL |
| `engine_ready_after_pod` | 0,3 s <sub>p5–p95 0,21–0,3, n=3</sub> | — | — |
| `engine_ready_total` | 1,5 s <sub>p5–p95 1,41–1,86, n=3</sub> | — | — |
| `pod_ready` | 1,3 s <sub>p5–p95 1,21–1,57, n=3</sub> | — | — |

- *runc* : V4-buildkit-rootless : moteur prêt en 1.4s ; engine_version=v0.35.1, storage_driver=overlayfs/native (buildkit)

- *runc* : V4-buildkit-rootless : moteur prêt en 1.9s ; engine_version=v0.35.1, storage_driver=overlayfs/native (buildkit)

- *runc* : V4-buildkit-rootless : moteur prêt en 1.5s ; engine_version=v0.35.1, storage_driver=overlayfs/native (buildkit)

- *kata:kata (rust)* : ERREUR : OcError: kubectl wait pod/ci --for=condition=Ready --timeout=300s -n kvr-4d877-dind-01-kata-v4-1 -> rc=1 : error: timed out waiting for the condition on pods/ci

- *kata:kata (rust)* : ERREUR : OcError: kubectl wait pod/ci --for=condition=Ready --timeout=300s -n kvr-4d877-dind-01-kata-v4-2 -> rc=1 : error: timed out waiting for the condition on pods/ci

- *kata:kata (rust)* : ERREUR : OcError: kubectl wait pod/ci --for=condition=Ready --timeout=300s -n kvr-4d877-dind-01-kata-v4-3 -> rc=1 : error: timed out waiting for the condition on pods/ci

- *kata:kata-qemu (go)* : ERREUR : OcError: kubectl wait pod/ci --for=condition=Ready --timeout=300s -n kvr-a47ff-dind-01-kata-v4-1 -> rc=1 : error: timed out waiting for the condition on pods/ci

- *kata:kata-qemu (go)* : ERREUR : OcError: kubectl wait pod/ci --for=condition=Ready --timeout=300s -n kvr-a47ff-dind-01-kata-v4-2 -> rc=1 : error: timed out waiting for the condition on pods/ci

- *kata:kata-qemu (go)* : ERREUR : OcError: kubectl wait pod/ci --for=condition=Ready --timeout=300s -n kvr-a47ff-dind-01-kata-v4-3 -> rc=1 : error: timed out waiting for the condition on pods/ci

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/DIND-01/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/DIND-01/kata) · [kata:kata-qemu (go)](../results/20261124-081741-ENV-A-47fc568/ENV-A/DIND-01/kata)

**Variante `V5-dind-privileged-memstore`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS 2/3 · ❌ FAIL 1/3 |
| `engine_ready_after_pod` | 16,8 s <sub>p5–p95 16,8–16,9, n=3</sub> | 83,7 s <sub>p5–p95 82,6–102, n=3</sub> ▼ +398 % | 68,7 s <sub>p5–p95 64,6–72,8, n=2</sub> ▼ +309 % |
| `engine_ready_total` | 18,3 s <sub>p5–p95 18,1–18,4, n=3</sub> | 118 s <sub>p5–p95 116–149, n=3</sub> ▼ +546 % | 206 s <sub>p5–p95 173–239, n=2</sub> ▼ +1027 % |
| `pod_ready` | 1,5 s <sub>p5–p95 1,32–1,59, n=3</sub> | 35,7 s <sub>p5–p95 32–46,5, n=3</sub> ▼ +2280 % | 138 s <sub>p5–p95 109–166, n=2</sub> ▼ +9073 % |

- *runc* : V5-dind-privileged-memstore : moteur prêt en 18.1s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *runc* : V5-dind-privileged-memstore : moteur prêt en 18.4s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *runc* : V5-dind-privileged-memstore : moteur prêt en 18.3s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *kata:kata (rust)* : V5-dind-privileged-memstore : moteur prêt en 115.3s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *kata:kata (rust)* : V5-dind-privileged-memstore : moteur prêt en 152.1s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *kata:kata (rust)* : V5-dind-privileged-memstore : moteur prêt en 118.2s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *kata:kata-qemu (go)* : ERREUR : OcError: kubectl wait pod/ci --for=condition=Ready --timeout=300s -n kvr-a47ff-dind-01-kata-v5-1 -> rc=1 : error: timed out waiting for the condition on pods/ci

- *kata:kata-qemu (go)* : V5-dind-privileged-memstore : moteur prêt en 169.6s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

- *kata:kata-qemu (go)* : V5-dind-privileged-memstore : moteur prêt en 243.0s ; storage_driver=overlayfs, cgroup_version=2, engine_version=29.10.0, security=[name=seccomp,profile=builtin name=cgroupns]

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/DIND-01/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/DIND-01/kata) · [kata:kata-qemu (go)](../results/20261124-081741-ENV-A-47fc568/ENV-A/DIND-01/kata)

### DIND-05 — Build Dockerfile multi-étapes (build-arg, secret, cache)

**Variante `V1-dind-privileged`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ❌ FAIL | ❌ FAIL |
| `build_cold` | 3,3 s <sub>p5–p95 3,21–3,57, n=3</sub> | — | — |
| `build_warm` | 0,2 s <sub>p5–p95 0,2–0,65, n=3</sub> | — | — |
| `image_verified` | 1 bool <sub>p5–p95 1–1, n=3</sub> | — | — |

- *runc* : V1-dind-privileged : build froid 3.2s, chaud 0.7s, image OK

- *runc* : V1-dind-privileged : build froid 3.3s, chaud 0.2s, image OK

- *runc* : V1-dind-privileged : build froid 3.6s, chaud 0.2s, image OK

- *kata:kata (rust)* : V1-dind-privileged : build en échec : fs/snapshots/4/work,upperdir=/var/lib/docker/containerd/daemon/io.containerd.snapshotter.v1.overlayfs/snapshots/4/fs,lowerdir=/var/lib/docker/containerd/daemon/io.containerd.snapshotter.v1.overlayfs/snapshots/3/fs,index=off,redirect_dir=off", err: invalid argument command terminated with exit code 1

- *kata:kata-qemu (go)* : V1-dind-privileged : build en échec : fs/snapshots/4/work,upperdir=/var/lib/docker/containerd/daemon/io.containerd.snapshotter.v1.overlayfs/snapshots/4/fs,lowerdir=/var/lib/docker/containerd/daemon/io.containerd.snapshotter.v1.overlayfs/snapshots/3/fs,index=off,redirect_dir=off", err: invalid argument command terminated with exit code 1

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-05/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-05/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/DIND-05/kata)

**Variante `V2-dind-rootless`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ⛔ NON SUPPORTÉ | ⛔ NON SUPPORTÉ |
| `build_cold` | 3,6 s <sub>p5–p95 3,15–3,78, n=3</sub> | — | — |
| `build_warm` | 0,2 s <sub>p5–p95 0,2–0,2, n=3</sub> | — | — |
| `image_verified` | 1 bool <sub>p5–p95 1–1, n=3</sub> | — | — |

- *runc* : V2-dind-rootless : build froid 3.8s, chaud 0.2s, image OK

- *runc* : V2-dind-rootless : build froid 3.6s, chaud 0.2s, image OK

- *runc* : V2-dind-rootless : build froid 3.1s, chaud 0.2s, image OK

- *kata:kata (rust)* : NON SUPPORTÉ : moteur V2-dind-rootless indisponible après 300s : error: cannot exec into a container in a completed pod; current phase is Failed

- *kata:kata-qemu (go)* : NON SUPPORTÉ : moteur V2-dind-rootless indisponible après 300s : error: cannot exec into a container in a completed pod; current phase is Failed

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-05/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-05/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/DIND-05/kata)

**Variante `V3-buildah`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ❌ FAIL | ❌ FAIL |
| `build_cold` | 6,3 s <sub>p5–p95 5,85–6,84, n=3</sub> | — | — |
| `build_warm` | 3 s <sub>p5–p95 3–3,09, n=3</sub> | — | — |
| `image_verified` | 1 bool <sub>p5–p95 1–1, n=3</sub> | — | — |

- *runc* : V3-buildah : build froid 6.3s, chaud 3.0s, image OK

- *runc* : V3-buildah : build froid 6.9s, chaud 3.1s, image OK

- *runc* : V3-buildah : build froid 5.8s, chaud 3.0s, image OK

- *kata:kata (rust)* : V3-buildah : build en échec : or setuid on /usr/bin/newuidmap: invalid argument 2026/11/24 15:30:35 WARN Falling back to single mapping Error: mounting an overlay over build context directory: creating overlay scaffolding for build context directory: exec /usr/bin/fuse-overlayfs: exit status 1 command terminated with exit code 1

- *kata:kata (rust)* : V3-buildah : build en échec : or setuid on /usr/bin/newuidmap: invalid argument 2026/11/24 15:31:59 WARN Falling back to single mapping Error: mounting an overlay over build context directory: creating overlay scaffolding for build context directory: exec /usr/bin/fuse-overlayfs: exit status 1 command terminated with exit code 1

- *kata:kata (rust)* : V3-buildah : build en échec : or setuid on /usr/bin/newuidmap: invalid argument 2026/11/24 15:33:43 WARN Falling back to single mapping Error: mounting an overlay over build context directory: creating overlay scaffolding for build context directory: exec /usr/bin/fuse-overlayfs: exit status 1 command terminated with exit code 1

- *kata:kata-qemu (go)* : V3-buildah : build en échec : or setuid on /usr/bin/newuidmap: invalid argument 2026/11/24 11:19:19 WARN Falling back to single mapping Error: mounting an overlay over build context directory: creating overlay scaffolding for build context directory: exec /usr/bin/fuse-overlayfs: exit status 1 command terminated with exit code 1

- *kata:kata-qemu (go)* : V3-buildah : build en échec : or setuid on /usr/bin/newuidmap: invalid argument 2026/11/24 11:20:28 WARN Falling back to single mapping Error: mounting an overlay over build context directory: creating overlay scaffolding for build context directory: exec /usr/bin/fuse-overlayfs: exit status 1 command terminated with exit code 1

- *kata:kata-qemu (go)* : V3-buildah : build en échec : or setuid on /usr/bin/newuidmap: invalid argument 2026/11/24 11:21:35 WARN Falling back to single mapping Error: mounting an overlay over build context directory: creating overlay scaffolding for build context directory: exec /usr/bin/fuse-overlayfs: exit status 1 command terminated with exit code 1

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-05/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-05/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/DIND-05/kata)

**Variante `V4-buildkit-rootless`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ❌ FAIL | ❌ FAIL |
| `build_cold` | 2,6 s <sub>p5–p95 2,42–2,69, n=3</sub> | — | — |
| `build_warm` | 0,8 s <sub>p5–p95 0,71–0,8, n=3</sub> | — | — |
| `image_verified` | 1 bool <sub>p5–p95 1–1, n=3</sub> | — | — |

- *runc* : V4-buildkit-rootless : build froid 2.7s, chaud 0.7s, image OK

- *runc* : V4-buildkit-rootless : build froid 2.6s, chaud 0.8s, image OK

- *runc* : V4-buildkit-rootless : build froid 2.4s, chaud 0.8s, image OK

- *kata:kata (rust)* : ERREUR : OcError: kubectl wait pod/ci --for=condition=Ready --timeout=300s -n kvr-1738a-dind-05-kata-v4-1 -> rc=1 : error: timed out waiting for the condition on pods/ci

- *kata:kata (rust)* : ERREUR : OcError: kubectl wait pod/ci --for=condition=Ready --timeout=300s -n kvr-1738a-dind-05-kata-v4-2 -> rc=1 : error: timed out waiting for the condition on pods/ci

- *kata:kata (rust)* : ERREUR : OcError: kubectl wait pod/ci --for=condition=Ready --timeout=300s -n kvr-1738a-dind-05-kata-v4-3 -> rc=1 : error: timed out waiting for the condition on pods/ci

- *kata:kata-qemu (go)* : ERREUR : OcError: kubectl wait pod/ci --for=condition=Ready --timeout=300s -n kvr-a5b1b-dind-05-kata-v4-1 -> rc=1 : error: timed out waiting for the condition on pods/ci

- *kata:kata-qemu (go)* : ERREUR : OcError: kubectl wait pod/ci --for=condition=Ready --timeout=300s -n kvr-a5b1b-dind-05-kata-v4-2 -> rc=1 : error: timed out waiting for the condition on pods/ci

- *kata:kata-qemu (go)* : ERREUR : OcError: kubectl wait pod/ci --for=condition=Ready --timeout=300s -n kvr-a5b1b-dind-05-kata-v4-3 -> rc=1 : error: timed out waiting for the condition on pods/ci

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-05/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-05/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/DIND-05/kata)

**Variante `V5-dind-privileged-memstore`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS 2/3 · ⛔ NON SUPPORTÉ 1/3 | ✅ PASS |
| `build_cold` | 2,8 s <sub>p5–p95 2,8–2,98, n=3</sub> | 193 s <sub>p5–p95 164–222, n=2</sub> ▼ +6793 % | 101 s <sub>p5–p95 101–120, n=3</sub> ▼ +3504 % |
| `build_warm` | 0,1 s <sub>p5–p95 0,1–0,1, n=3</sub> | 76,3 s <sub>p5–p95 65,5–87,2, n=2</sub> ▼ +76250 % | 27,5 s <sub>p5–p95 17,4–32,9, n=3</sub> ▼ +27400 % |
| `image_verified` | 1 bool <sub>p5–p95 1–1, n=3</sub> | 1 bool <sub>p5–p95 1–1, n=2</sub> | 1 bool <sub>p5–p95 1–1, n=3</sub> |

- *runc* : V5-dind-privileged-memstore : build froid 3.0s, chaud 0.1s, image OK

- *runc* : V5-dind-privileged-memstore : build froid 2.8s, chaud 0.1s, image OK

- *kata:kata (rust)* : V5-dind-privileged-memstore : build froid 225.1s, chaud 88.4s, image OK

- *kata:kata (rust)* : NON SUPPORTÉ : moteur V5-dind-privileged-memstore indisponible après 300s : kubectl exec -n kvr-1738a-dind-05-kata-v5-2 ci -c engine -- sh -c docker info >/dev/null 2>&1 && echo ok : délai dépassé (60s)

- *kata:kata (rust)* : V5-dind-privileged-memstore : build froid 160.9s, chaud 64.3s, image OK

- *kata:kata-qemu (go)* : V5-dind-privileged-memstore : build froid 100.6s, chaud 16.3s, image OK

- *kata:kata-qemu (go)* : V5-dind-privileged-memstore : build froid 122.5s, chaud 27.5s, image OK

- *kata:kata-qemu (go)* : V5-dind-privileged-memstore : build froid 100.9s, chaud 33.5s, image OK

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-05/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-05/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/DIND-05/kata)

### DIND-06 — Conteneurs imbriqués : réseau et MTU

**Variante `V1-dind-privileged`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ❌ FAIL 2/3 · ⛔ NON SUPPORTÉ 1/3 | ❌ FAIL |
| `nested_https_ok` | 1 bool <sub>p5–p95 1–1, n=3</sub> | 0 bool <sub>p5–p95 0–0, n=2</sub> | 0 bool <sub>p5–p95 0–0, n=3</sub> |
| `nested_https_time` | 348 ms <sub>p5–p95 302–456, n=3</sub> | — | — |

- *runc* : V1-dind-privileged : MTU pod=1400 bridge docker=1500 ; HTTPS depuis un conteneur imbriqué : OK (code 200)

- *kata:kata (rust)* : NON SUPPORTÉ : moteur V1-dind-privileged indisponible après 300s : kubectl exec -n kvr-1738a-dind-06-kata-v1-1 ci -c engine -- sh -c docker info >/dev/null 2>&1 && echo ok : délai dépassé (60s)

- *kata:kata (rust)* : V1-dind-privileged : MTU pod=1400 bridge docker=1500 ; conteneur imbriqué NON démarré (rc=125) : docker: Error response from daemon: failed to mount /tmp/containerd-mount1064430347: mount source: "overlay", target: "/tmp/containerd-mount1064430347", fstype: overlay, flags: 0, data: "workdir=/var/lib/docker/container

- *kata:kata (rust)* : V1-dind-privileged : MTU pod=1400 bridge docker=1500 ; conteneur imbriqué NON démarré (rc=125) : docker: Error response from daemon: failed to mount /tmp/containerd-mount152662713: mount source: "overlay", target: "/tmp/containerd-mount152662713", fstype: overlay, flags: 0, data: "workdir=/var/lib/docker/containerd/

- *kata:kata-qemu (go)* : V1-dind-privileged : MTU pod=1400 bridge docker=1500 ; conteneur imbriqué NON démarré (rc=125) : docker: Error response from daemon: failed to mount /tmp/containerd-mount998523465: mount source: "overlay", target: "/tmp/containerd-mount998523465", fstype: overlay, flags: 0, data: "workdir=/var/lib/docker/containerd/

- *kata:kata-qemu (go)* : V1-dind-privileged : MTU pod=1400 bridge docker=1500 ; conteneur imbriqué NON démarré (rc=125) : docker: Error response from daemon: failed to mount /tmp/containerd-mount2847004510: mount source: "overlay", target: "/tmp/containerd-mount2847004510", fstype: overlay, flags: 0, data: "workdir=/var/lib/docker/container

- *kata:kata-qemu (go)* : V1-dind-privileged : MTU pod=1400 bridge docker=1500 ; conteneur imbriqué NON démarré (rc=125) : docker: Error response from daemon: failed to mount /tmp/containerd-mount4061591174: mount source: "overlay", target: "/tmp/containerd-mount4061591174", fstype: overlay, flags: 0, data: "workdir=/var/lib/docker/container

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-06/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-06/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/DIND-06/kata)

**Variante `V2-dind-rootless`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ⛔ NON SUPPORTÉ | ⛔ NON SUPPORTÉ |
| `nested_https_ok` | 1 bool <sub>p5–p95 1–1, n=3</sub> | — | — |
| `nested_https_time` | 352 ms <sub>p5–p95 347–386, n=3</sub> | — | — |

- *runc* : V2-dind-rootless : MTU pod=1400 bridge docker=1500 ; HTTPS depuis un conteneur imbriqué : OK (code 200)

- *kata:kata (rust)* : NON SUPPORTÉ : moteur V2-dind-rootless indisponible après 300s : error: cannot exec into a container in a completed pod; current phase is Failed

- *kata:kata-qemu (go)* : NON SUPPORTÉ : moteur V2-dind-rootless indisponible après 300s : error: cannot exec into a container in a completed pod; current phase is Failed

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-06/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-06/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/DIND-06/kata)

**Variante `V5-dind-privileged-memstore`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS 2/3 · ⛔ NON SUPPORTÉ 1/3 | ✅ PASS |
| `nested_https_ok` | 1 bool <sub>p5–p95 1–1, n=3</sub> | 1 bool <sub>p5–p95 1–1, n=2</sub> | 1 bool <sub>p5–p95 1–1, n=3</sub> |
| `nested_https_time` | 342 ms <sub>p5–p95 284–705, n=3</sub> | 842 ms <sub>p5–p95 817–868, n=2</sub> ▼ +146 % | 930 ms <sub>p5–p95 825–1 178, n=3</sub> ▼ +172 % |

- *runc* : V5-dind-privileged-memstore : MTU pod=1400 bridge docker=1500 ; HTTPS depuis un conteneur imbriqué : OK (code 200)

- *kata:kata (rust)* : V5-dind-privileged-memstore : MTU pod=1400 bridge docker=1500 ; HTTPS depuis un conteneur imbriqué : OK (code 200)

- *kata:kata (rust)* : NON SUPPORTÉ : moteur V5-dind-privileged-memstore indisponible après 300s : kubectl exec -n kvr-1738a-dind-06-kata-v5-2 ci -c engine -- sh -c docker info >/dev/null 2>&1 && echo ok : délai dépassé (60s)

- *kata:kata-qemu (go)* : V5-dind-privileged-memstore : MTU pod=1400 bridge docker=1500 ; HTTPS depuis un conteneur imbriqué : OK (code 200)

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-06/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-06/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/DIND-06/kata)

### DIND-14 — Étape malveillante : accès au disque du nœud

**Variante `V1-dind-privileged`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ⛔ NON SUPPORTÉ | ⛔ NON SUPPORTÉ |
| `block_devices_mountable` | 4 count | — | — |
| `node_rootfs_mounted` | 1 bool | — | — |

- *runc* : runc : 4 partition(s) montée(s) depuis le conteneur imbriqué ; système de fichiers du NŒUD ACCESSIBLE (via vda4:partage)

- *kata:kata (rust)* : NON SUPPORTÉ : conteneur imbriqué non lancé (rc=125) : scénario non exécutable ; command terminated with exit code 125

- *kata:kata-qemu (go)* : NON SUPPORTÉ : conteneur imbriqué non lancé (rc=125) : scénario non exécutable ; command terminated with exit code 125

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-14/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-14/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/DIND-14/kata)

**Variante `V5-dind-privileged-memstore`**

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `block_devices_mountable` | 4 count | 1 count ≈ -75 % (non significatif) | 1 count ≈ -75 % (non significatif) |
| `node_rootfs_mounted` | 1 bool | 0 bool | 0 bool |

- *runc* : runc : 4 partition(s) montée(s) depuis le conteneur imbriqué ; système de fichiers du NŒUD ACCESSIBLE (via vda4:partage)

- *kata:kata (rust)* : kata : 1 partition(s) montée(s) depuis le conteneur imbriqué ; système de fichiers du NŒUD non accessible

- *kata:kata-qemu (go)* : kata : 1 partition(s) montée(s) depuis le conteneur imbriqué ; système de fichiers du NŒUD non accessible

Résultats bruts : [runc](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-14/runc) · [kata:kata (rust)](../results/20261124-145018-ENV-A-8a85ad9/ENV-A/DIND-14/kata) · [kata:kata-qemu (go)](../results/20261124-104157-ENV-A-8a85ad9/ENV-A/DIND-14/kata)

## Agents IA

### AGT-08 — Latence d'un appel d'outil (exec)

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `exec_failures` | 0 count <sub>p5–p95 0–0, n=3</sub> | 0 count <sub>p5–p95 0–0, n=3</sub> — | 0 count <sub>p5–p95 0–0, n=3</sub> — |
| `exec_latency_p50` | 61 ms <sub>p5–p95 60,1–61, n=3</sub> | 237 ms <sub>p5–p95 226–250, n=3</sub> ▼ +289 % | 287 ms <sub>p5–p95 208–310, n=3</sub> ▼ +370 % |
| `exec_latency_p95` | 75 ms <sub>p5–p95 74,1–75, n=3</sub> | 318 ms <sub>p5–p95 310–326, n=3</sub> ▼ +324 % | 489 ms <sub>p5–p95 359–544, n=3</sub> ▼ +552 % |

- *runc* : 100 exec : p50 61 ms, p95 75 ms, échecs 0

- *runc* : 100 exec : p50 60 ms, p95 74 ms, échecs 0

- *kata:kata (rust)* : 100 exec : p50 225 ms, p95 309 ms, échecs 0

- *kata:kata (rust)* : 100 exec : p50 251 ms, p95 318 ms, échecs 0

- *kata:kata (rust)* : 100 exec : p50 237 ms, p95 327 ms, échecs 0

- *kata:kata-qemu (go)* : 100 exec : p50 287 ms, p95 489 ms, échecs 0

- *kata:kata-qemu (go)* : 100 exec : p50 199 ms, p95 345 ms, échecs 0

- *kata:kata-qemu (go)* : 100 exec : p50 313 ms, p95 550 ms, échecs 0

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/AGT-08/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/AGT-08/kata) · [kata:kata-qemu (go)](../results/20261124-081741-ENV-A-47fc568/ENV-A/AGT-08/kata)

### AGT-14 — Accès à l'API Kubernetes et aux métadonnées

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `api_denied` | 1 bool | 1 bool | 1 bool |
| `metadata_unreachable` | 1 bool | 1 bool | 1 bool |
| `sa_token_present` | 0 bool | 0 bool | 0 bool |

- *runc* : token SA présent=False ; API sans identité → HTTP 403 ; métadonnées → 000

- *kata:kata (rust)* : token SA présent=False ; API sans identité → HTTP 403 ; métadonnées → 000

- *kata:kata-qemu (go)* : token SA présent=False ; API sans identité → HTTP 403 ; métadonnées → 000

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/AGT-14/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/AGT-14/kata) · [kata:kata-qemu (go)](../results/20261124-081741-ENV-A-47fc568/ENV-A/AGT-14/kata)

### AGT-17 — Multiplication de processus (bornée)

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ❌ FAIL |
| `container_killed` | 1 bool | 0 bool | — |
| `pids_max_in_container` | — | 336 count | — |
| `processes_reached` | — | 325 count | — |

- *runc* : runc : 6000 processus tentés ; pids.max conteneur=max ; contenu par limite mémoire : conteneur tué en 2.0s (raison=OOMKilled, code=137, memory.max=268435456) avant toute limite pids

- *kata:kata (rust)* : kata : 6000 processus tentés ; pids.max conteneur=336 ; contenu par limite pids (336) : 325 processus, forks refusés=compteurs illisibles (plus de pids disponibles, exec rc=254)

- *kata:kata-qemu (go)* : ERREUR : OcError: kubectl exec -n kvr-a47ff-agt-17-kata-1 probe -- bash -c pids=(); last=; i=0; for ((i=1; i<=6000; i++)); do sleep 600 & if [ "$!" = "$last" ] \|\| (( SECONDS > 90 )); then break; fi; last=$!; pids+=($!); (( i % 25 == 0 )) && echo $i > /tmp/kvr-agt17; done 2>/dev/null; n=${#pids[@]}; echo $n > /tmp/kvr-agt17; read pe < /sys/fs/cgroup/pids.events; echo "DONE $n $SECONDS $pe"; kill -9 "${pids[@]}" 2>/dev/null; wait 2>/dev/null; exit 0 : délai dépassé (300s)

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/AGT-17/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/AGT-17/kata) · [kata:kata-qemu (go)](../results/20261124-081741-ENV-A-47fc568/ENV-A/AGT-17/kata)

### AGT-20 — Arrêt d'urgence (processus ignorant SIGTERM)

| | runc | kata:kata (rust) | kata:kata-qemu (go) |
|---|---|---|---|
| Statut | ✅ PASS | ✅ PASS | ✅ PASS |
| `beyond_grace` | 3,3 s <sub>p5–p95 3,3–3,39, n=3</sub> | -1,6 s <sub>p5–p95 -1,6–-1,6, n=3</sub> ▲ -148 % | -0,5 s <sub>p5–p95 -0,86–0,04, n=3</sub> ▲ -115 % |
| `time_to_gone` | 8,3 s <sub>p5–p95 8,3–8,39, n=3</sub> | 3,4 s <sub>p5–p95 3,4–3,4, n=3</sub> ▲ -59 % | 4,5 s <sub>p5–p95 4,14–5,04, n=3</sub> ▲ -46 % |

- *runc* : runc : pod supprimé en 8.4s (grâce 5s, dépassement 3.4s)

- *runc* : runc : pod supprimé en 8.3s (grâce 5s, dépassement 3.3s)

- *kata:kata (rust)* : kata : pod supprimé en 3.4s (grâce 5s, dépassement -1.6s)

- *kata:kata-qemu (go)* : kata : pod supprimé en 4.1s (grâce 5s, dépassement -0.9s)

- *kata:kata-qemu (go)* : kata : pod supprimé en 4.5s (grâce 5s, dépassement -0.5s)

- *kata:kata-qemu (go)* : kata : pod supprimé en 5.1s (grâce 5s, dépassement 0.1s)

Résultats bruts : [runc](../results/20261123-205546-ENV-A-a20e314/ENV-A/AGT-20/runc) · [kata:kata (rust)](../results/20261123-205546-ENV-A-a20e314/ENV-A/AGT-20/kata) · [kata:kata-qemu (go)](../results/20261124-081741-ENV-A-47fc568/ENV-A/AGT-20/kata)

## Volumes

### VOL-01 — Stockage : montage, écriture, persistance (backend local)

| | runc | kata:kata (rust) |
|---|---|---|
| Statut | ✅ PASS | ✅ PASS |
| `data_persisted` | 1 bool | 1 bool |
| `pod_ready_with_pvc` | 2,1 s | 19,5 s ≈ +827 % (non significatif) |
| `write_seq_with_sync` | 323 MB/s | 32 MB/s ≈ -90 % (non significatif) |

- *runc* : runc : crc-csi-hostpath-provisioner (kubevirt.io.hostpath-provisioner), montage vu dans le conteneur « /dev/vda4 xfs » ; écriture 64 MiB + sync 323.0 MB/s ; données identiques après recréation du pod ; 0:1001070000:2775 id=1001070000:0 groups=0,1001070000

- *kata:kata (rust)* : kata : crc-csi-hostpath-provisioner (kubevirt.io.hostpath-provisioner), montage vu dans le conteneur « none virtiofs » ; écriture 64 MiB + sync 32.0 MB/s ; données identiques après recréation du pod ; 0:1001080000:2775 id=1001080000:0 groups=0,1001080000

Résultats bruts : [runc](../results/20261124-141740-ENV-A-8a85ad9/ENV-A/VOL-01/runc) · [kata:kata (rust)](../results/20261124-141740-ENV-A-8a85ad9/ENV-A/VOL-01/kata)

### VOL-12 — Pod compromis : accès aux volumes des autres pods

| | runc | kata:kata (rust) |
|---|---|---|
| Statut | ✅ PASS | ✅ PASS |
| `block_devices_mountable` | 4 count | 1 count ≈ -75 % (non significatif) |
| `victim_volume_reached` | 1 bool | 0 bool |

- *runc* : attaquant runc privilégié : 4 périphérique(s) monté(s) (loop0, vda2, vda3, vda4) ; volume de la victime (crc-csi-hostpath-provisioner) ATTEINT sur vda4

- *kata:kata (rust)* : attaquant kata privilégié : 1 périphérique(s) monté(s) (vda1) ; volume de la victime (crc-csi-hostpath-provisioner) non atteint

Résultats bruts : [runc](../results/20261124-194458-ENV-A-cf3e9e3/ENV-A/VOL-12/runc) · [kata:kata (rust)](../results/20261124-194458-ENV-A-cf3e9e3/ENV-A/VOL-12/kata)

## Secrets

### SCR-01 — Secret natif : tous les modes de consommation

| | runc | kata:kata (rust) |
|---|---|---|
| Statut | ✅ PASS | ✅ PASS |
| `mismatched_paths` | 0 count | 0 count — |
| `pod_ready` | 0,91 s | 21 s ≈ +2211 % (non significatif) |

- *runc* : runc : 8/8 contenus identiques ; downward API OK ; volume optional absent : pod démarré ; mode items 440 0 1000970000 ; types de montage ['tmpfs']

- *kata:kata (rust)* : kata : 8/8 contenus identiques ; downward API OK ; volume optional absent : pod démarré ; mode items 440 0 1000980000 ; types de montage ['tmpfs', 'virtiofs']

Résultats bruts : [runc](../results/20261124-141740-ENV-A-8a85ad9/ENV-A/SCR-01/runc) · [kata:kata (rust)](../results/20261124-141740-ENV-A-8a85ad9/ENV-A/SCR-01/kata)

### SCR-02 — Secret natif : propagation d'une rotation

| | runc | kata:kata (rust) |
|---|---|---|
| Statut | ✅ PASS | ✅ PASS |
| `env_updated` | 0 bool | 0 bool |
| `propagation_few` | 2,3 s | 85,6 s ≈ +3622 % (non significatif) |
| `propagation_many` | 2,3 s | 85,6 s ≈ +3622 % (non significatif) |
| `subpath_updated` | 0 bool | 0 bool |

- *runc* : runc : rotation propagée en 2.3 s (3 clés), 2.3 s (40 clés) ; subPath non mis à jour (attendu) ; variable d'environnement inchangée (attendu)

- *kata:kata (rust)* : kata : rotation propagée en 85.6 s (3 clés), 85.6 s (40 clés) ; subPath non mis à jour (attendu) ; variable d'environnement inchangée (attendu)

Résultats bruts : [runc](../results/20261124-141740-ENV-A-8a85ad9/ENV-A/SCR-02/runc) · [kata:kata (rust)](../results/20261124-141740-ENV-A-8a85ad9/ENV-A/SCR-02/kata)

### SCR-03 — Token de ServiceAccount projeté : rotation

| | runc | kata:kata (rust) |
|---|---|---|
| Statut | ✅ PASS | ✅ PASS |
| `api_accepts_initial_token` | 1 bool | 1 bool |
| `api_accepts_rotated_token` | 1 bool | 1 bool |
| `rotation_after` | 532 s | 499 s ≈ -6 % (non significatif) |

- *runc* : runc : token initial (durée 600 s, aud ['https://kubernetes.default.svc']) → HTTP 200 ; nouveau token (émis 532 s après le premier) vu dans le conteneur (sondage toutes les 15 s), HTTP 200

- *kata:kata (rust)* : kata : token initial (durée 600 s, aud ['https://kubernetes.default.svc']) → HTTP 200 ; nouveau token (émis 499 s après le premier) vu dans le conteneur (sondage toutes les 15 s), HTTP 200

Résultats bruts : [runc](../results/20261124-194458-ENV-A-cf3e9e3/ENV-A/SCR-03/runc) · [kata:kata (rust)](../results/20261124-194458-ENV-A-cf3e9e3/ENV-A/SCR-03/kata)

### SCR-04 — Secret lisible par l'administrateur du nœud ?

| | runc | kata:kata (rust) |
|---|---|---|
| Statut | ✅ PASS | ✅ PASS |
| `readable_node_tmpfs` | 1 bool | 1 bool |
| `readable_proc_environ` | 1 bool | 0 bool |
| `readable_process_memory` | 1 bool | 1 bool |

- *runc* : runc : depuis le nœud, secret LU dans le tmpfs du kubelet, LU dans /proc/<pid>/environ, LU dans la mémoire de sleep ; processus du pod vus sur le nœud : conmon(6 MiB), sleep(4 MiB)

- *kata:kata (rust)* : kata : depuis le nœud, secret LU dans le tmpfs du kubelet, absent dans /proc/<pid>/environ, LU dans la mémoire de containerd-shim, virtiofsd, qemu-system-aar ; processus du pod vus sur le nœud : containerd-shim(36 MiB), virtiofsd(18 MiB), qemu-system-aar(329 MiB), vhost-3553425(0 MiB), vhost-3553425(0 MiB)

Résultats bruts : [runc](../results/20261124-141740-ENV-A-8a85ad9/ENV-A/SCR-04/runc) · [kata:kata (rust)](../results/20261124-141740-ENV-A-8a85ad9/ENV-A/SCR-04/kata)

### SCR-05 — Pod compromis : collecte des secrets des autres pods du nœud

| | runc | kata:kata (rust) |
|---|---|---|
| Statut | ✅ PASS | ✅ PASS |
| `stolen_from_kata` | 1 bool | 0 bool |
| `stolen_from_runc` | 1 bool | 0 bool |

- *runc* : attaquant runc (hostPath kubelet en lecture seule) : secret de la victime runc VOLÉ, de la victime Kata VOLÉ ; répertoires des pods visibles : runc=True, kata=True ; montages sous /host : 251

- *kata:kata (rust)* : attaquant kata (hostPath kubelet en lecture seule) : secret de la victime runc non lu, de la victime Kata non lu ; répertoires des pods visibles : runc=True, kata=True ; montages sous /host : 1

Résultats bruts : [runc](../results/20261124-141740-ENV-A-8a85ad9/ENV-A/SCR-05/runc) · [kata:kata (rust)](../results/20261124-141740-ENV-A-8a85ad9/ENV-A/SCR-05/kata)
