#!/bin/bash
cd "$(dirname "$0")"

PID_FILE="floating_note.pid"
STOPPED=0

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    sleep 0.3
    if kill -0 "$PID" 2>/dev/null; then
      kill -9 "$PID" 2>/dev/null || true
    fi
    echo "[stop] Stopped process PID=$PID"
    STOPPED=1
  fi
  rm -f "$PID_FILE"
fi

if [ "$STOPPED" -eq 0 ]; then
  echo "[stop] Floating Note is not running."
else
  echo "[stop] Done."
fi
