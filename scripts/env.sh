# shellcheck shell=bash
# Préparation commune à ./precheck et ./run : outils requis + environnement Python.
#
# Poste connecté : uv installe Python et les dépendances exactes du uv.lock.
# Site airgappé (miroir Artifactory) :
#   export KVR_PYPI_INDEX=https://artifactory.example/api/pypi/pypi-remote/simple
#   + Python ≥ 3.12 : soit présent sur le poste (UV_PYTHON=/usr/bin/python3.12, UV_PYTHON_DOWNLOADS=never),
#     soit via un miroir des builds Python (UV_PYTHON_INSTALL_MIRROR=https://artifactory.example/…).
#   Les versions ET les hashes du uv.lock sont imposés : le miroir doit servir les mêmes fichiers que PyPI.

missing=0
need() {
  if command -v "$1" >/dev/null 2>&1; then return 0; fi
  echo "✘ $1 introuvable : $2" >&2
  missing=1
}
need kubectl "https://kubernetes.io/docs/tasks/tools/ (macOS : brew install kubectl ; site : dépôt generic Artifactory)"
need uv      "https://docs.astral.sh/uv/ (macOS : brew install uv ; site : binaire uv depuis Artifactory)"
need git     "https://git-scm.com/"
[ "$missing" -eq 0 ] || exit 1

if [ -n "${KVR_PYPI_INDEX:-}" ]; then
  # uv sync --frozen télécharge depuis les URL pypi.org du lockfile : on passe par un export épinglé.
  if [ ! -x .venv/bin/python ] || [ uv.lock -nt .venv/.kvr-synced ]; then
    uv venv --quiet --allow-existing
    uv export --frozen --format requirements-txt --no-emit-project --quiet -o .venv/requirements.txt
    uv pip install --quiet --require-hashes --index-url "$KVR_PYPI_INDEX" -r .venv/requirements.txt
    touch .venv/.kvr-synced
  fi
  KVR_PY=(uv run --no-sync)
else
  uv sync --frozen --quiet
  KVR_PY=(uv run --frozen)
fi
