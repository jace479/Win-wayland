#!/usr/bin/env bash
# ==============================================================================
# ntKDE Stop Desktop Session
# ==============================================================================

set -eo pipefail

if [[ "${HOME:-}" == *":"* ]] || [[ ! -d "${HOME:-}" ]]; then
    export HOME="$(getent passwd "$(id -u)" | cut -d: -f6)"
fi
export USER="$(id -un)"
export USER_ID="$(id -u)"

now=$(date "+%Y-%m-%d %H:%M:%S")
echo "=========================================================="
echo "[$now] Stopping ntKDE Plasma Session (User: $USER)"
echo "=========================================================="

# Kill script loops FIRST so they do not auto-restart killed services
SCRIPT_PATTERNS=(
    "start-panels.sh"
    "kde-task-bridge.py"
    "foreign_window_presenter.py"
    "kscreen_backend_launcher"
    "plasmawindowed"
)

for pat in "${SCRIPT_PATTERNS[@]}"; do
    pkill -u "$USER_ID" -9 -f "$pat" 2>/dev/null || true
done

TARGETS=(
    "plasmashell"
    "kwin_wayland"
    "kwin_x11"
    "startplasma-wayland"
    "startplasma-x11"
    "weston"
    "krunner"
    "kactivitymanagerd"
    "kded6"
    "kded5"
    "kglobalaccel6"
    "kglobalaccel5"
    "Xephyr"
)

# Phase 1: Graceful SIGTERM
for proc in "${TARGETS[@]}"; do
    if pgrep -u "$USER_ID" -x "$proc" >/dev/null 2>&1; then
        echo "Sending SIGTERM to $proc..."
        pkill -u "$USER_ID" -TERM -x "$proc" 2>/dev/null || true
    fi
done

sleep 0.5

# Phase 2: Forceful SIGKILL for lingering processes
for proc in "${TARGETS[@]}"; do
    if pgrep -u "$USER_ID" -x "$proc" >/dev/null 2>&1; then
        echo "Forcing SIGKILL to $proc..."
        pkill -u "$USER_ID" -KILL -x "$proc" 2>/dev/null || true
    fi
done

# Clean up socket and lock files
RUNTIME_DIR="/run/user/$USER_ID"
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1 "$RUNTIME_DIR/nt-plasma-"* 2>/dev/null || true

echo "ntKDE Plasma session stopped successfully."
