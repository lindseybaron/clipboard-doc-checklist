#!/usr/bin/env bash
set -euo pipefail

LABEL="com.clipto.watcher"
OLD_LABEL="com.clipboard-doc-checklist.watcher"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
OLD_PLIST_PATH="$HOME/Library/LaunchAgents/$OLD_LABEL.plist"

echo "[launchd] uninstalling $LABEL"

launchctl bootout "gui/$UID/$LABEL" >/dev/null 2>&1 || true
launchctl bootout "gui/$UID" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootout "gui/$UID/$OLD_LABEL" >/dev/null 2>&1 || true
launchctl bootout "gui/$UID" "$OLD_PLIST_PATH" >/dev/null 2>&1 || true

if [[ -f "$PLIST_PATH" ]]; then
  rm -f "$PLIST_PATH"
  echo "[done] removed plist: $PLIST_PATH"
else
  echo "[info] plist not found: $PLIST_PATH"
fi

if [[ -f "$OLD_PLIST_PATH" ]]; then
  rm -f "$OLD_PLIST_PATH"
  echo "[done] removed legacy plist: $OLD_PLIST_PATH"
fi

echo "[done] launch agent removed"
