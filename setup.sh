#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"
UV="${UV:-$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")}"
PLIST_LABEL="local.car-maintenance-bot"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
# shellcheck disable=SC1091
. ./.env 2>/dev/null || true
LOG_PATH="${BOT_CRON_LOG_PATH:-${PROJECT_DIR}/logs/bot.log}"

if [ ! -f .env ]; then
  echo "No .env found. Copy .env-example to .env and fill it in first."
  exit 1
fi

echo "==> Syncing dependencies"
"$UV" sync

echo "==> Initialising database"
"$UV" run src/init_db.py

echo "==> Checking Subaru device registration"
"$UV" run src/register_device.py

mkdir -p "$(dirname "${LOG_PATH}")"

echo "==> Installing launchd agent (daily at 12:00)"
cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PROJECT_DIR}/run-bot</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${PROJECT_DIR}</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>12</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${LOG_PATH}</string>
  <key>StandardErrorPath</key>
  <string>${LOG_PATH}</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/${PLIST_LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"

echo "Setup complete. The bot runs daily at 12:00 and logs to ${LOG_PATH}."
