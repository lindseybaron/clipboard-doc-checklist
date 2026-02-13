#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.clipto.watcher"
OLD_LABEL="com.clipboard-doc-checklist.watcher"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
OLD_PLIST_PATH="$HOME/Library/LaunchAgents/$OLD_LABEL.plist"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
WATCHER_SCRIPT="$ROOT_DIR/tools/clipto_watcher.py"
LOG_DIR="$ROOT_DIR/logs"
OUT_LOG="$LOG_DIR/launchd.out.log"
ERR_LOG="$LOG_DIR/launchd.err.log"

echo "[launchd] installing $LABEL"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[error] missing virtualenv python: $PYTHON_BIN"
  echo "Run: bash scripts/bootstrap.sh"
  exit 1
fi

if [[ ! -f "$WATCHER_SCRIPT" ]]; then
  echo "[error] watcher script not found: $WATCHER_SCRIPT"
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$LOG_DIR"

cat >"$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_BIN</string>
    <string>$WATCHER_SCRIPT</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$ROOT_DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$OUT_LOG</string>
  <key>StandardErrorPath</key>
  <string>$ERR_LOG</string>
</dict>
</plist>
EOF

# Remove previously loaded job if present (ignore failures).
launchctl bootout "gui/$UID/$OLD_LABEL" >/dev/null 2>&1 || true
launchctl bootout "gui/$UID" "$OLD_PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootout "gui/$UID/$LABEL" >/dev/null 2>&1 || true
launchctl bootout "gui/$UID" "$PLIST_PATH" >/dev/null 2>&1 || true

if [[ -f "$OLD_PLIST_PATH" ]]; then
  rm -f "$OLD_PLIST_PATH"
fi

launchctl bootstrap "gui/$UID" "$PLIST_PATH"
launchctl enable "gui/$UID/$LABEL" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$UID/$LABEL" >/dev/null 2>&1 || true

echo "[done] installed and started: $LABEL"
echo "[info] plist: $PLIST_PATH"
echo "[info] logs:  $OUT_LOG / $ERR_LOG"
echo "[info] status:"
launchctl print "gui/$UID/$LABEL" | sed -n '1,20p'
