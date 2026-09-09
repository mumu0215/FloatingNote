#!/bin/bash
cd "$(dirname "$0")"

if [ -n "${FLOATING_NOTE_DATA:-}" ]; then
  DATA_DIR="$FLOATING_NOTE_DATA"
elif [ -n "${XDG_DATA_HOME:-}" ]; then
  DATA_DIR="$XDG_DATA_HOME/FloatingNote"
else
  DATA_DIR="$HOME/.local/share/FloatingNote"
fi
PID_FILE="$DATA_DIR/floating_note.pid"
LEGACY_PID="floating_note.pid"
STOPPED=0

stop_pid_file() {
  local file="$1"
  if [ ! -f "$file" ]; then
    return 0
  fi
  local PID
  PID="$(cat "$file" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    sleep 0.3
    if kill -0 "$PID" 2>/dev/null; then
      kill -9 "$PID" 2>/dev/null || true
    fi
    echo "[stop] Stopped process PID=$PID"
    STOPPED=1
  fi
  rm -f "$file"
}

stop_pid_file "$PID_FILE"
stop_pid_file "$LEGACY_PID"

if [ "$STOPPED" -eq 0 ]; then
  echo "[stop] Floating Note is not running."
else
  echo "[stop] Done."
fi
