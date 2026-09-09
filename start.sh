#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ -n "${FLOATING_NOTE_DATA:-}" ]; then
  DATA_DIR="$FLOATING_NOTE_DATA"
elif [ -n "${XDG_DATA_HOME:-}" ]; then
  DATA_DIR="$XDG_DATA_HOME/FloatingNote"
else
  DATA_DIR="$HOME/.local/share/FloatingNote"
fi
mkdir -p "$DATA_DIR"
PID_FILE="$DATA_DIR/floating_note.pid"
LEGACY_PID="floating_note.pid"

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[start] Floating Note is already running. PID=$OLD_PID"
    exit 0
  fi
fi
if [ -f "$LEGACY_PID" ]; then
  OLD_PID="$(cat "$LEGACY_PID" 2>/dev/null || true)"
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
nohup python src/main.py > "$DATA_DIR/floating_note.log" 2>&1 &
# App writes its own pid file under DATA_DIR; keep a brief fallback for scripts
echo $! > "$PID_FILE"
echo "[start] Floating Note started. PID=$(cat "$PID_FILE")"
echo "[start] Data dir: $DATA_DIR"
