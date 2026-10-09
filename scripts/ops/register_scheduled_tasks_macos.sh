#!/usr/bin/env bash
# Register (or re-register) the NSE-session-gated orchestrator as a macOS launchd agent.
#
#   com.nifty.orchestrator   Mon-Fri 09:10 local time -> run_if_session.py orchestrator
#
# The macOS counterpart of register_scheduled_tasks.ps1. run_if_session.py skips
# NSE holidays and weekends itself and logs to data/ops/scheduled_runs.log; the
# orchestrator stops itself at 15:50. With NIFTY_PROFILE=trading in .env (written
# by `scripts/bootstrap.py init`) its morning catch-up is the Upstox seed refresh,
# so no second evening job is needed.
#
# launchd fires on the Mac's LOCAL clock: set the system time zone to Asia/Kolkata,
# or shift the hour below. A Mac that is asleep at 09:10 misses the run — schedule
# a wake as well:  sudo pmset repeat wakeorpoweron MTWRF 09:05:00
#
# Usage:
#   scripts/ops/register_scheduled_tasks_macos.sh            # install / replace
#   scripts/ops/register_scheduled_tasks_macos.sh --remove   # uninstall
#   PYTHON=/path/to/python scripts/ops/register_scheduled_tasks_macos.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LABEL="com.nifty.orchestrator"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
HOUR="${HOUR:-9}"
MINUTE="${MINUTE:-10}"

if [[ "${1:-}" == "--remove" ]]; then
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    echo "removed $LABEL"
    exit 0
fi

if [[ -z "${PYTHON:-}" ]]; then
    if [[ -x "$ROOT/.venv/bin/python" ]]; then
        PYTHON="$ROOT/.venv/bin/python"
    else
        PYTHON="$(command -v python3)"
    fi
fi
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 11), sys.version' \
    || { echo "need Python 3.11+ at $PYTHON (set PYTHON=...)"; exit 1; }

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs"

intervals=""
for weekday in 1 2 3 4 5; do
    intervals+="
        <dict><key>Weekday</key><integer>$weekday</integer><key>Hour</key><integer>$HOUR</integer><key>Minute</key><integer>$MINUTE</integer></dict>"
done

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <!-- caffeinate keeps the Mac awake for exactly as long as the orchestrator runs -->
        <string>/usr/bin/caffeinate</string>
        <string>-i</string>
        <string>$PYTHON</string>
        <string>$ROOT/scripts/ops/run_if_session.py</string>
        <string>orchestrator</string>
    </array>
    <key>WorkingDirectory</key><string>$ROOT</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>PYTHONIOENCODING</key><string>utf-8</string>
    </dict>
    <key>StartCalendarInterval</key>
    <array>$intervals
    </array>
    <key>StandardOutPath</key><string>$ROOT/logs/launchd_orchestrator.log</string>
    <key>StandardErrorPath</key><string>$ROOT/logs/launchd_orchestrator.log</string>
</dict>
</plist>
EOF

plutil -lint "$PLIST" >/dev/null
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "registered $LABEL Mon-Fri $(printf '%02d:%02d' "$HOUR" "$MINUTE") local -> $PYTHON"
echo "run now:  launchctl kickstart gui/$(id -u)/$LABEL"
