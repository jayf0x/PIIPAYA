#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

source src-python/.venv/bin/activate

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64)
    TARGET_TRIPLE="aarch64-apple-darwin"
    ;;
  Darwin-x86_64)
    TARGET_TRIPLE="x86_64-apple-darwin"
    ;;
  Linux-x86_64)
    TARGET_TRIPLE="x86_64-unknown-linux-gnu"
    ;;
  Linux-aarch64)
    TARGET_TRIPLE="aarch64-unknown-linux-gnu"
    ;;
  *)
    echo "Unsupported platform: $(uname -s)-$(uname -m)"
    exit 1
    ;;
esac

OUTPUT_NAME="deid-sidecar-${TARGET_TRIPLE}"
OUTPUT_DIR="$REPO_ROOT/src-tauri/binaries"

python -m pip install -r src-python/requirements.txt
pyinstaller \
  --clean \
  --onefile \
  --name "$OUTPUT_NAME" \
  src-python/__main__.py

mkdir -p "$OUTPUT_DIR"
cp "dist/$OUTPUT_NAME" "$OUTPUT_DIR/$OUTPUT_NAME"
chmod +x "$OUTPUT_DIR/$OUTPUT_NAME"

echo "Built sidecar: $OUTPUT_DIR/$OUTPUT_NAME"
