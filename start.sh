#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "[1/2] Creating Python virtual environment (.venv)..."
  python3 -m venv .venv
fi

if [ ! -f ".venv/.deps_installed_v1" ]; then
  echo "[2/2] Installing dependencies..."
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
  touch .venv/.deps_installed_v1
fi

echo "Starting Browser Use AI Studio..."
exec .venv/bin/python app.py "$@"
