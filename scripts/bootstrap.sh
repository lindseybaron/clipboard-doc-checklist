#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
CONFIG_FILE="$ROOT_DIR/config.json"
EXAMPLE_CONFIG="$ROOT_DIR/config.example.json"

echo "[bootstrap] project root: $ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[error] python3 is required but was not found on PATH."
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[bootstrap] creating virtual environment..."
  python3 -m venv "$VENV_DIR"
else
  echo "[bootstrap] using existing virtual environment."
fi

echo "[bootstrap] upgrading pip..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip

echo "[bootstrap] installing dependencies..."
"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements.txt"

if [[ ! -f "$CONFIG_FILE" ]]; then
  cp "$EXAMPLE_CONFIG" "$CONFIG_FILE"
  echo "[bootstrap] created config.json from config.example.json"
else
  echo "[bootstrap] config.json already exists."
fi

cat <<'EOF'
[done] Bootstrap complete.

Next steps:
1) Edit config.json with your web_app_url and other values.
2) Run the watcher:
   source .venv/bin/activate
   python tools/todo_it_clipboard.py
EOF
