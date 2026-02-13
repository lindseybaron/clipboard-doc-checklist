#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCHD_UNINSTALL_SCRIPT="$ROOT_DIR/scripts/uninstall_launchagent.sh"
VENV_DIR="$ROOT_DIR/.venv"
CONFIG_FILE="$ROOT_DIR/config.json"
LOG_DIR="$ROOT_DIR/logs"

REMOVE_VENV=false
REMOVE_CONFIG=false
REMOVE_LOGS=false
ASSUME_YES=false

usage() {
  cat <<'EOF'
Usage: bash scripts/uninstall.sh [options]

Removes launchd auto-start and optionally deletes local project artifacts.

Options:
  --remove-venv      Delete .venv
  --remove-config    Delete config.json
  --remove-logs      Delete logs directory
  --remove-all       Delete .venv, config.json, and logs
  --yes              Skip confirmation prompts
  -h, --help         Show this help message
EOF
}

for arg in "$@"; do
  case "$arg" in
    --remove-venv)
      REMOVE_VENV=true
      ;;
    --remove-config)
      REMOVE_CONFIG=true
      ;;
    --remove-logs)
      REMOVE_LOGS=true
      ;;
    --remove-all)
      REMOVE_VENV=true
      REMOVE_CONFIG=true
      REMOVE_LOGS=true
      ;;
    --yes)
      ASSUME_YES=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[error] unknown argument: $arg"
      usage
      exit 1
      ;;
  esac
done

confirm() {
  local prompt="$1"
  if [[ "$ASSUME_YES" == "true" ]]; then
    return 0
  fi

  if [[ ! -t 0 ]]; then
    return 1
  fi

  local reply
  read -r -p "$prompt [y/N] " reply
  case "$reply" in
    y|Y|yes|YES)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

echo "[uninstall] starting cleanup in $ROOT_DIR"

if [[ -f "$LAUNCHD_UNINSTALL_SCRIPT" ]]; then
  bash "$LAUNCHD_UNINSTALL_SCRIPT"
else
  echo "[warn] launchd uninstall script not found: $LAUNCHD_UNINSTALL_SCRIPT"
fi

if [[ "$REMOVE_VENV" == "true" ]]; then
  if [[ -d "$VENV_DIR" ]]; then
    if confirm "Delete virtual environment at $VENV_DIR?"; then
      rm -rf "$VENV_DIR"
      echo "[done] removed: $VENV_DIR"
    else
      echo "[skip] kept virtual environment: $VENV_DIR"
    fi
  else
    echo "[info] virtual environment not found: $VENV_DIR"
  fi
fi

if [[ "$REMOVE_CONFIG" == "true" ]]; then
  if [[ -f "$CONFIG_FILE" ]]; then
    if confirm "Delete config file at $CONFIG_FILE?"; then
      rm -f "$CONFIG_FILE"
      echo "[done] removed: $CONFIG_FILE"
    else
      echo "[skip] kept config file: $CONFIG_FILE"
    fi
  else
    echo "[info] config file not found: $CONFIG_FILE"
  fi
fi

if [[ "$REMOVE_LOGS" == "true" ]]; then
  if [[ -d "$LOG_DIR" ]]; then
    if confirm "Delete logs directory at $LOG_DIR?"; then
      rm -rf "$LOG_DIR"
      echo "[done] removed: $LOG_DIR"
    else
      echo "[skip] kept logs directory: $LOG_DIR"
    fi
  else
    echo "[info] logs directory not found: $LOG_DIR"
  fi
fi

cat <<'EOF'
[done] Uninstall complete.
EOF
