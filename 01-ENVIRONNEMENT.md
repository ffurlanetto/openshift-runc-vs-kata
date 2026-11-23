# 01 — Environnement de test : état des lieux, manques, installation

> Audit réalisé le 2026-11-23 sur le poste de test. Relançable avec `scripts/check-env.sh`.

## 1. Synthèse

| Élément | État | Impact |
|---|---|---|
| OpenShift Local (CRC) 2.62.0, OCP 4.22.1, MicroShift 4.22.0 | ✅ Running (operator `image-registry` dégradé) | OK pour runc |
| Architecture du nœud | ⚠️ **arm64** (Apple M5 Max, VM vfkit) | Voir §3 : support Red Hat de Kata |
| Ressources VM CRC | ⚠️ 8 vCPU / 15 Go RAM / 35 Go disque, ~12 Go RAM déjà utilisés | Trop juste pour des tests de densité Kata |
| `/dev/kvm` dans la VM CRC | ❌ **Absent** | **Bloquant** : Kata ne peut pas lancer de micro-VM |
| Virtualisation imbriquée | ❌ `vfkit` supporte `--nested`, mais CRC ne passe pas l'option | Contournement possible (§3.1) |
| Operator OpenShift Sandboxed Containers (OSC) | ⚠️ v1.13.1 au catalogue, **architectures supportées : amd64, s390x uniquement** | Pas d'OSC supporté sur arm64 (§3.2) |
| RuntimeClass existantes | aucune (runtimes CRI-O : `runc`, `crun`) | Normal avant installation |
| Metrics API (`oc adm top`) | ❌ indisponible (monitoring désactivé par défaut dans CRC) | Nécessaire pour les mesures d'overhead |
| `agent-sandbox-operator` (Agent Sandbox : `Sandbox`, `SandboxTemplate`, `SandboxClaim`, `SandboxWarmPool`) | ⚠️ v0.9.0, canal **preview**, **amd64 uniquement** | Sur ENV-A : projet upstream `kubernetes-sigs/agent-sandbox` |
| Backend LLM pour les tests d'agents | ❌ à choisir | API distante (clé + egress) ou modèle local sur le Mac (Ollama, via `host.crc.testing`) |
| Operators sécurité au catalogue | ✅ `compliance-operator`, `security-profiles-operator`, `file-integrity-operator` | Utilisables pour le volet sécurité |

## 2. Outils sur le poste (macOS arm64)

| Outil | État | Usage dans la campagne | Installation |
|---|---|---|---|
| `crc` 2.62.0 | ✅ | Cluster | — |
| `oc` 4.22.1 | ⚠️ présent dans `~/.crc/bin/oc/` mais pas dans le `PATH` | Toutes les opérations | `eval $(crc oc-env)` (à mettre dans `~/.zshrc`) |
| `kubectl` 1.37.1 | ✅ | Alternative à `oc` | — |
| `helm` 4.2.4 | ✅ | Installation `kata-deploy` (si arm64) | — |
| `podman` 6.0.2 | ✅ | Build de l'image d'outillage de bench | — |
| `jq` | ✅ | Parsing des résultats | — |
| `git`, `go` | ✅ | Scripts | — |
| `uv` 0.13.0 | ✅ | Gestion Python (venv + dépendances, Python récent indépendant du `python3` 3.9.6 système) | — |
| `yq` | ❌ | Manipulation des manifestes YAML | `brew install yq` |
| `k6` | ❌ | Charge HTTP / latence applicative | `brew install k6` |
| `hey` | ❌ | Charge HTTP simple | `brew install hey` |
| `trivy` | ❌ | Scan d'images / config | `brew install trivy` |
| `kubescape` | ❌ | Posture sécurité (NSA/CIS) | `brew install kubescape` |
| `pandoc` | ❌ | Export du rapport comité (PDF/DOCX) | `brew install pandoc` (+ `brew install --cask basictex` pour PDF) |
| Python `pyyaml`, `pandas`, `matplotlib`, `jinja2`, `jsonschema` | ✅ (installé via `uv sync`) | Agrégation des résultats et graphiques | `uv sync` (déclarés dans `pyproject.toml`) |
| `docker` | ❌ | Non nécessaire (podman suffit) | — |

Outils **exécutés dans les pods** (pas d'installation locale nécessaire, ils seront embarqués dans une image d'outillage `kata-bench` construite avec podman) :
`fio`, `iperf3`, `sysbench`, `stress-ng`, `netperf`, `redis-benchmark`, `pgbench`, `amicontained`, `cdk` (container escape toolkit), `deepce`.
Outils **exécutés comme Job dans le cluster** : `kube-bench`, `kube-hunter`.

### Installation en une fois

```bash
brew install yq k6 hey trivy kubescape pandoc
echo 'eval $(crc oc-env)' >> ~/.zshrc && eval $(crc oc-env)
uv sync            # crée .venv (Python 3.12) avec les dépendances de pyproject.toml
# exécution des scripts : uv run scripts/aggregate.py ...
```

## 3. Points bloquants pour Kata et options

### 3.1 Pas de `/dev/kvm` dans la VM CRC

Kata lance chaque pod dans une micro-VM (QEMU/KVM). Sur ce poste, cela implique de la **virtualisation imbriquée** :
macOS (Hypervisor.framework) → VM CRC (RHCOS) → micro-VM Kata.

- Le matériel le permet (Apple M3+ et macOS 15+ ; ici M5 Max / macOS 27, `kern.hv_support: 1`).
- `vfkit` a l'option `-n, --nested`, mais **CRC 2.62 ne l'expose pas** (`crc config` n'a pas d'option nested).

**Contournement proposé** (modifie un binaire système, il faut `sudo`, réversible) :

```bash
crc stop
sudo mv /usr/local/crc/vfkit /usr/local/crc/vfkit.real
sudo tee /usr/local/crc/vfkit >/dev/null <<'EOF'
#!/bin/sh
case "$1" in --version|-v|--help|-h) exec /usr/local/crc/vfkit.real "$@";; esac
exec /usr/local/crc/vfkit.real --nested "$@"
EOF
sudo chmod 755 /usr/local/crc/vfkit
crc config set memory 24576   # 24 Go recommandés pour Kata (overhead par pod)
crc config set cpus 12
crc config set disk-size 80
crc config set enable-cluster-monitoring true
crc start
# Vérification :
ssh -i ~/.crc/machines/crc/id_ed25519 -p 2222 core@127.0.0.1 'ls -l /dev/kvm'
```

Retour arrière : `sudo mv /usr/local/crc/vfkit.real /usr/local/crc/vfkit`. Une mise à jour de CRC écrase le wrapper.

### 3.2 L'operator OSC n'est pas supporté sur arm64

Le CSV `sandboxed-containers-operator.v1.13.1` déclare `arch.amd64` et `arch.s390x` uniquement. Sur CRC arm64 :

| Option | Fidélité à la production OpenShift | Coût | Usage recommandé |
|---|---|---|---|
| **A. Kata upstream via `kata-deploy` (Helm) sur CRC arm64 + nested** | Moyenne : même technologie (Kata 3.x, QEMU, CRI-O handler), mais pas le packaging/support Red Hat, pas de `KataConfig` | Faible | Tests **fonctionnels et sécurité**, découverte des limites |
| **B. OCP x86_64 sur bare metal (ou instance cloud *metal*) + OSC 1.13** | Élevée : stack supportée Red Hat | Moyen à élevé | Tests de **performance, densité, exploitation** et validation finale |
| C. CRC sur un poste x86_64 avec nested KVM | Bonne pour le fonctionnel (OSC installable), perf non représentative | Faible | Alternative à A si un poste Linux x86 est disponible |

**Recommandation** : options **A puis B**. A permet de démarrer tout de suite les campagnes fonctionnelle et sécurité. Les chiffres de performance obtenus sur CRC (double niveau de virtualisation, nœud unique) sont **indicatifs uniquement** et ne doivent pas être présentés au comité comme des valeurs de référence. Le plan de tests marque les tests qui exigent l'environnement B.

### 3.3 Autres points d'attention CRC

- **Nœud unique** : pas de tests de drain/migration multi-nœuds, pas de réseau inter-nœuds.
- **`image-registry` dégradé** : pousser l'image d'outillage sur un registre externe (quay.io) ou réparer le registre interne (`oc patch configs.imageregistry.operator.openshift.io cluster --type merge -p '{"spec":{"managementState":"Managed","storage":{"emptyDir":{}}}}'`).
- **podman machine** (4 vCPU / 3,7 Go) tourne en parallèle : l'arrêter pendant les mesures (`podman machine stop`) pour limiter le bruit.
