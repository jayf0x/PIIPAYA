#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

HOST="127.0.0.1"
PORT="4173"
DB_PATH="$REPO_ROOT/deid.db"

OLLAMA_MODEL=""
RUN_OLLAMA_E2E="0"

if [ -f "$DB_PATH" ]; then
  DETECTED="$(python - <<'PY'
import json
import sqlite3
from pathlib import Path

db_path = Path("deid.db")
if not db_path.exists():
    print("|0")
    raise SystemExit(0)

conn = sqlite3.connect(db_path)
try:
    row_model = conn.execute("SELECT value FROM config WHERE key = 'ollama_model'").fetchone()
    row_enabled = conn.execute("SELECT value FROM config WHERE key = 'ollama_enabled'").fetchone()
finally:
    conn.close()

model = ""
enabled = False
if row_model and row_model[0] is not None:
    try:
        model = str(json.loads(row_model[0])).strip()
    except Exception:
        model = str(row_model[0]).strip()
if row_enabled and row_enabled[0] is not None:
    try:
        enabled = bool(json.loads(row_enabled[0]))
    except Exception:
        enabled = str(row_enabled[0]).strip().lower() in {"1", "true", "yes", "on"}

print(f"{model}|{1 if (enabled and model) else 0}")
PY
)"
  OLLAMA_MODEL="${DETECTED%%|*}"
  RUN_OLLAMA_E2E="${DETECTED##*|}"
fi

bun run dev:web --host "$HOST" --port "$PORT" >/tmp/deid-wdio-dev.log 2>&1 &
VITE_PID=$!

cleanup() {
  if kill -0 "$VITE_PID" >/dev/null 2>&1; then
    kill "$VITE_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

for _ in {1..30}; do
  if curl -fsS "http://$HOST:$PORT" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

DEID_OLLAMA_MODEL="$OLLAMA_MODEL" DEID_RUN_OLLAMA_E2E="$RUN_OLLAMA_E2E" bunx wdio run wdio.conf.js
