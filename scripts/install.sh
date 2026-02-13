#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOOTSTRAP_SCRIPT="$ROOT_DIR/scripts/bootstrap.sh"
LAUNCHD_SCRIPT="$ROOT_DIR/scripts/install_launchagent.sh"
CONFIG_FILE="$ROOT_DIR/config.json"

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
  python tools/todo_it_clipboard.py
EOF
