# 01 — Environnement de test : état des lieux, manques, installation

> Audit réalisé le 2026-11-23 sur le poste de test. Relançable avec `./precheck`.

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
| Disque de la VM CRC | ❌ **87 % utilisé (30/35 Go) → nœud en DiskPressure**, plus aucun pod planifiable | **Bloquant** : `crc config set disk-size 80` (à faire avec le redémarrage `--nested`) |
| APIService `v1beta1.external.metrics.k8s.io` (KEDA) | ❌ indisponible (pods KEDA non planifiables) | Les namespaces supprimés restent en `Terminating` |
| Kyverno | ❌ absent sur CRC | `./setup kyverno` (chart 3.10.0, Kyverno v1.20.0) |
| Operators sécurité au catalogue | ✅ `compliance-operator`, `security-profiles-operator`, `file-integrity-operator` | Utilisables pour le volet sécurité |

## 2. Prérequis du poste qui lance le banc

Le banc est portable : il pilote **n'importe quel cluster** OpenShift ou Kubernetes, local ou distant, uniquement via `kubectl`. Le contexte kube est choisi au lancement. `./precheck` vérifie tout ce qui suit.

| Outil | Requis pour | Statut | Installation (poste connecté) | Site airgappé |
|---|---|---|---|---|
| `kubectl` | tout (`oc` n'est **pas** nécessaire) | obligatoire | `brew install kubectl` | binaire depuis un dépôt generic Artifactory ; version ±1 mineure du cluster |
| `uv` | Python + dépendances du banc | obligatoire | `brew install uv` | binaire depuis Artifactory ; `KVR_PYPI_INDEX` = index PyPI miroir ; Python ≥ 3.12 local (`UV_PYTHON`, `UV_PYTHON_DOWNLOADS=never`) ou `UV_PYTHON_INSTALL_MIRROR` |
| `git` | traçabilité (commit de chaque campagne) | obligatoire | Xcode CLT / paquet système | paquet système |
| `bash` | wrappers `./precheck`, `./run`, `./setup` | obligatoire | — | — |
| `helm` | `./setup` (Kyverno, et plus tard Kata, Jenkins, ARC, Agent Sandbox) | phases POL/DIND/AGT, sur cluster de test | `brew install helm` | binaire + charts OCI via miroir (réécriture `registry.mirrors`) |
| `pandoc` | export PDF/DOCX du rapport comité | optionnel | `brew install pandoc` | — |

Plus besoin d'installer en local `jq`, `yq`, `k6`, `hey`, `trivy` ou `kubescape` : les outils de charge et de scan tournent **dans des pods**, à partir d'images épinglées et mirrorables.

État constaté sur le poste de test (2026-11-23) : `kubectl` 1.37.1, `uv` 0.13.0, `git`, `helm` 4.2.4 présents.
Avertissement : `kubectl` 1.37 face à un serveur 1.35 dépasse l'écart supporté (±1). C'est fonctionnel pour le banc, mais il vaut mieux un client 1.35/1.36.

### Images et outils sur site airgappé (miroir Artifactory)

- **Images** : toutes déclarées et épinglées par digest dans `campaign.yaml › images`. `./run --print-images` donne la liste à mirrorer.
- **Accès au miroir**, deux modes :
  - le cluster gère le miroir (OpenShift `ImageDigestMirrorSet`, miroirs containerd) : rien à configurer ;
  - réécriture par le banc : règles `registry.mirrors` (préfixe → préfixe), globales ou par profil de cluster.
- **Digest** : il reste identique si le dépôt Artifactory est un *remote* (proxy) du registre d'origine, donc la reproductibilité est conservée.
- **Secret de pull** : `registry.pull_secret`, copié depuis un namespace du cluster ou créé depuis un fichier `dockerconfigjson` local, puis attaché au ServiceAccount de chaque namespace de test.
- **Charts Helm** : `campaign.yaml › charts`, même réécriture (dépôt OCI Artifactory).
- **Dépendances Python** : `export KVR_PYPI_INDEX=https://artifactory…/api/pypi/<repo>/simple`. Les versions **et hashes** du `uv.lock` sont imposés.

  Attention : `uv sync --frozen` ignore les miroirs et télécharge depuis les URL pypi.org du lockfile. Constat vérifié le 2026-11-23, d'où le passage par un export épinglé quand `KVR_PYPI_INDEX` est défini.
- **Pré-vérification** : le precheck tire réellement chaque image via le miroir et signale `ErrImagePull` ou `ImagePullBackOff` avec la cause probable.

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
