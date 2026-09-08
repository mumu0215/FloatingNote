#!/bin/bash
set -e
cd "$(dirname "$0")"

PID_FILE="floating_note.pid"

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[start] Floating Note is already running. PID=$OLD_PID"
    exit 0
  fi
fi

if [ ! -d ".venv" ]; then
  echo "[start] Creating virtual environment..."
  python3 -m venv .venv || { echo "[start] Failed to create venv"; exit 1; }
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install -r requirements.txt -q || { echo "[start] Failed to install deps"; exit 1; }
fi

# shellcheck disable=SC1091
source .venv/bin/activate
nohup python src/main.py > floating_note.log 2>&1 &
echo $! > "$PID_FILE"
echo "[start] Floating Note started. PID=$(cat "$PID_FILE")"
