#!/usr/bin/env bash
# Active la virtualisation imbriquée pour OpenShift Local (CRC) sur macOS Apple Silicon (M3+, macOS 15+),
# nécessaire à Kata Containers (/dev/kvm dans la VM CRC).
#
# CRC ne propose pas d'option pour cela : vfkit est remplacé par un wrapper qui ajoute --nested.
# Réversible, idempotent. Une mise à jour de CRC écrase le wrapper (relancer « enable »).
#
#   sudo scripts/crc/nested-virt.sh enable    # installe le wrapper
#   sudo scripts/crc/nested-virt.sh disable   # restaure le vfkit d'origine
#   scripts/crc/nested-virt.sh status
set -euo pipefail

VFKIT=/usr/local/crc/vfkit
REAL=/usr/local/crc/vfkit.real
MARK="# kvr-nested-wrapper"

is_wrapper() { [ -f "$VFKIT" ] && grep -q "$MARK" "$VFKIT" 2>/dev/null; }

case "${1:-status}" in
  enable)
    [ "$(id -u)" -eq 0 ] || { echo "à lancer avec sudo" >&2; exit 1; }
    [ "$(sysctl -n kern.hv_support)" = "1" ] || { echo "Hypervisor.framework indisponible" >&2; exit 1; }
    if is_wrapper; then echo "wrapper déjà en place"; exit 0; fi
    "$VFKIT" --help 2>&1 | grep -q -- "--nested" || { echo "ce vfkit ne supporte pas --nested" >&2; exit 1; }
    mv "$VFKIT" "$REAL"
    cat > "$VFKIT" <<EOF
#!/bin/sh
$MARK : ajoute --nested (virtualisation imbriquée pour Kata). Original : $REAL
case "\$1" in --version|-v|--help|-h|"") exec "$REAL" "\$@";; esac
exec "$REAL" --nested "\$@"
EOF
    chmod 755 "$VFKIT"
    echo "wrapper installé ; redémarrer CRC (crc stop && crc start)"
    ;;
  disable)
    [ "$(id -u)" -eq 0 ] || { echo "à lancer avec sudo" >&2; exit 1; }
    if ! is_wrapper; then echo "pas de wrapper en place"; exit 0; fi
    mv "$REAL" "$VFKIT"
    echo "vfkit d'origine restauré ; redémarrer CRC"
    ;;
  status)
    if is_wrapper; then echo "wrapper --nested : installé"; else echo "wrapper --nested : absent"; fi
    if pgrep -fl "vfkit.real --nested" >/dev/null || pgrep -fl "vfkit --nested" >/dev/null; then
      echo "VM CRC lancée avec --nested : oui"
    else
      echo "VM CRC lancée avec --nested : non"
    fi
    ;;
  *) echo "usage : $0 enable|disable|status" >&2; exit 1 ;;
esac
