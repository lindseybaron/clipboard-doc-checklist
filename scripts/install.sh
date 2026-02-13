#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOOTSTRAP_SCRIPT="$ROOT_DIR/scripts/bootstrap.sh"
LAUNCHD_SCRIPT="$ROOT_DIR/scripts/install_launchagent.sh"
CONFIG_FILE="$ROOT_DIR/config.json"
PREPARE_HEADINGS_SCRIPT="$ROOT_DIR/tools/prepare_doc_headings.py"
VERSION="0.1.0"
PREPARE_HEADINGS=false

print_usage() {
  cat <<'EOF'
Usage: bash scripts/install.sh [--prepare-headings] [--help] [--version]

Options:
  --prepare-headings   Create missing Google Doc H1 sections from config tag_map.
  --help               Show this help text and exit.
  --version            Print install script version and exit.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --prepare-headings)
      PREPARE_HEADINGS=true
      ;;
    --help|-h)
      print_usage
      exit 0
      ;;
    --version)
      echo "clipto-install $VERSION"
      exit 0
      ;;
    *)
      echo "[error] unknown argument: $arg"
      print_usage
      exit 1
      ;;
  esac
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "[error] python3 is required but was not found on PATH."
  exit 1
fi

if ! python3 - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 9) else 1)
PY
then
  PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")' 2>/dev/null || echo "unknown")"
  echo "[error] python3 >= 3.9 is required. Found: ${PY_VERSION}."
  echo "[hint] install a newer Python (recommended: 3.9+) and ensure 'python3' points to it."
  exit 1
fi

echo "[install] starting setup in $ROOT_DIR"

if [[ ! -x "$BOOTSTRAP_SCRIPT" ]]; then
  chmod +x "$BOOTSTRAP_SCRIPT"
fi
bash "$BOOTSTRAP_SCRIPT"

echo "[install] validating config.json"
python3 - <<'PY' "$CONFIG_FILE"
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
if not config_path.exists():
    raise SystemExit("[error] config.json not found after bootstrap")

cfg = json.loads(config_path.read_text(encoding="utf-8"))
errors = []
warnings = []

web_app_url = str(cfg.get("web_app_url", "")).strip()
if not web_app_url:
    errors.append("web_app_url is missing")
elif "<YOUR_DEPLOYMENT_ID>" in web_app_url or "<REPLACE" in web_app_url:
    errors.append("web_app_url still contains placeholder text")
elif not web_app_url.startswith("https://script.google.com/"):
    warnings.append("web_app_url does not look like an Apps Script URL")

tag_map = cfg.get("tag_map", {})
if not isinstance(tag_map, dict) or not tag_map:
    errors.append("tag_map must be a non-empty object")

for key, value in (tag_map.items() if isinstance(tag_map, dict) else []):
    if ":" in str(key):
        errors.append(f"tag_map key '{key}' should not include ':'")
    if not str(value).strip():
        errors.append(f"tag_map value for '{key}' is empty")

if errors:
    print("[error] config validation failed:")
    for e in errors:
        print(f" - {e}")
    print("\nUpdate config.json, then rerun: bash scripts/install.sh")
    raise SystemExit(1)

print("[done] config validation passed")
if warnings:
    print("[warn] review these warnings:")
    for w in warnings:
        print(f" - {w}")
PY

if [[ "$PREPARE_HEADINGS" == "true" ]]; then
  echo "[install] preparing document headings from config tag_map"
  python3 "$PREPARE_HEADINGS_SCRIPT"
fi

if [[ -t 0 ]]; then
  read -r -p "Install auto-start at login via launchd? [y/N] " REPLY
  case "$REPLY" in
    y|Y|yes|YES)
      if [[ ! -x "$LAUNCHD_SCRIPT" ]]; then
        chmod +x "$LAUNCHD_SCRIPT"
      fi
      bash "$LAUNCHD_SCRIPT"
      ;;
    *)
      echo "[install] skipping launchd auto-start setup"
      ;;
  esac
else
  echo "[install] non-interactive shell; skipping launchd prompt"
fi

cat <<'EOF'
[done] Install completed.

Run manually anytime:
  source .venv/bin/activate
  python tools/clipto_watcher.py
EOF
