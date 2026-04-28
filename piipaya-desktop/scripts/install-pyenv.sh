#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if [ -f ".python-version" ]; then
  PY_VERSION="$(cat .python-version)"
else
  PY_VERSION="3.12.4"
fi

VENV_DIR="$REPO_ROOT/src-python/.venv"

# can change the default model
SPACY_MODEL="en_core_web_lg"


if ! command -v pyenv &>/dev/null; then
  echo "pyenv not found. Install: https://github.com/pyenv/pyenv"
  exit 1
fi

if ! pyenv versions --bare | grep -qx "$PY_VERSION"; then
  echo "Installing Python $PY_VERSION..."
  pyenv install "$PY_VERSION"
fi

if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ] && grep -q "/piipaya/piipaya/" "$VENV_DIR/bin/activate"; then
  echo "Removing broken venv at $VENV_DIR..."
  rm -rf "$VENV_DIR"
fi

export PYENV_VERSION="$PY_VERSION"
PYTHON_BIN="$(pyenv which python)"

# setup venv
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating venv at $VENV_DIR..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip --quiet
python -m pip install -r src-python/requirements.txt

echo "Downloading spaCy model..."
python -m spacy download "$SPACY_MODEL"

echo "Verifying environment..."
echo "python: $(which python)"
python -V
# python - <<'PY'
# import spacy
# print(f"spacy model '{'en_core_web_lg'}' installed: {spacy.util.is_package('en_core_web_lg')}")
# PY

echo ""
echo "Done. Activate the venv with: source src-python/.venv/bin/activate"
