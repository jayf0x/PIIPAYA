#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

source src-python/.venv/bin/activate
export PYTHONPATH="$REPO_ROOT/src-python"
python -m unittest discover -s src-python/tests -p "test_*.py" -v
