#!/usr/bin/env bash
set -Eeuo pipefail

log_dir="${XDG_STATE_HOME:-$HOME/.local/state}/nt-plasma"
mkdir -p "$log_dir"
log_file="$log_dir/plasma.log"
exec >>"$log_file" 2>&1

USER_ID="$(id -u)"
now=$(date "+%Y-%m-%d %H:%M:%S")
echo "========================================================"
echo "[$now] Stopping KDE Plasma session & applications (User: $USER)"
echo "========================================================"

TARGETS=(
    "plasmashell"
    "krunner"
    "kded5"
    "kactivitymanagerd"
    "kglobalaccel5"
    "klauncher"
    "dolphin"
    "konsole"
    "systemsettings"
)

# Phase 1: Graceful SIGTERM
for proc in "${TARGETS[@]}"; do
    if pgrep -u "$USER_ID" -x "$proc" >/dev/null 2>&1; then
        echo "[$now] Sending SIGTERM to $proc..."
        pkill -u "$USER_ID" -TERM -x "$proc" 2>/dev/null || true
    fi
done

sleep 1.5

# Phase 2: Forceful SIGKILL for any stubborn lingering processes
for proc in "${TARGETS[@]}"; do
    if pgrep -u "$USER_ID" -x "$proc" >/dev/null 2>&1; then
        echo "[$(date "+%Y-%m-%d %H:%M:%S")] Forcing SIGKILL to $proc..."
        pkill -u "$USER_ID" -KILL -x "$proc" 2>/dev/null || true
    fi
done

echo "[$(date "+%Y-%m-%d %H:%M:%S")] KDE Plasma session stopped successfully."
