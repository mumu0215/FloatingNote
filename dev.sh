#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "[dev] Creating virtual environment..."
  python3 -m venv .venv || { echo "[dev] Failed to create venv"; exit 1; }
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -r requirements.txt -q || { echo "[dev] Failed to install deps"; exit 1; }

echo "[dev] Starting Floating Note..."
python src/main.py
