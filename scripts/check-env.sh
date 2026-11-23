#!/usr/bin/env bash
# Inventaire de l'environnement de test runc vs Kata sur OpenShift Local.
# Usage : scripts/check-env.sh   (sortie lisible + code retour = nb de manques bloquants)
set -u
OC="$(command -v oc || echo "$HOME/.crc/bin/oc/oc")"
export KUBECONFIG="${KUBECONFIG:-$HOME/.crc/machines/crc/kubeconfig}"
blocking=0
ok()   { printf "  \033[32mOK\033[0m   %s\n" "$*"; }
ko()   { printf "  \033[31mKO\033[0m   %s\n" "$*"; }
warn() { printf "  \033[33mWARN\033[0m %s\n" "$*"; }

echo "== Outils locaux"
for t in crc oc kubectl helm podman jq git uv; do
  if command -v "$t" >/dev/null || { [ "$t" = oc ] && [ -x "$OC" ]; }; then ok "$t"; else ko "$t (requis)"; blocking=$((blocking+1)); fi
done
for t in yq k6 hey trivy kubescape pandoc; do
  command -v "$t" >/dev/null && ok "$t" || warn "$t manquant -> brew install $t"
done
( cd "$(dirname "$0")/.." && uv run --frozen python -c "import yaml,pandas,matplotlib,jinja2" ) >/dev/null 2>&1 && ok "python libs (uv)" || warn "python libs -> uv sync"

echo "== Cluster"
if crc status -o json 2>/dev/null | jq -e '.openshiftStatus=="Running" or .openshiftStatus=="Degraded"' >/dev/null; then
  ok "CRC $(crc status -o json | jq -r .openshiftVersion) ($(crc status -o json | jq -r .openshiftStatus))"
else ko "CRC non démarré (crc start)"; blocking=$((blocking+1)); fi
arch=$("$OC" get node -o jsonpath='{.items[0].status.nodeInfo.architecture}' 2>/dev/null)
[ "$arch" = amd64 ] && ok "arch nœud: $arch" || warn "arch nœud: $arch (OSC non supporté -> kata-deploy upstream)"
"$OC" get runtimeclass -o name 2>/dev/null | grep -q kata && ok "RuntimeClass kata présente" || warn "RuntimeClass kata absente"
"$OC" adm top node >/dev/null 2>&1 && ok "Metrics API" || warn "Metrics API indisponible (crc config set enable-cluster-monitoring true)"

echo "== VM CRC"
SSH="ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -i $HOME/.crc/machines/crc/id_ed25519 -p 2222 core@127.0.0.1"
if $SSH 'test -c /dev/kvm'; then ok "/dev/kvm présent (nested OK)"; else ko "/dev/kvm absent -> voir 01-ENVIRONNEMENT.md §3.1"; blocking=$((blocking+1)); fi
mem=$($SSH "free -g | awk '/Mem:/{print \$2}'")
[ "${mem:-0}" -ge 20 ] && ok "RAM VM ${mem}G" || warn "RAM VM ${mem}G (<20G, densité Kata limitée)"

echo "== Bloquants: $blocking"
exit "$blocking"
