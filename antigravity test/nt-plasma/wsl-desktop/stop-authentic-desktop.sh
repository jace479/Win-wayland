#!/usr/bin/env bash
set -eo pipefail

USER_ID="$(id -u)"
now=$(date "+%Y-%m-%d %H:%M:%S")
echo "=========================================================="
echo "[$now] Stopping Authentic Linux Desktop session (User: $USER)"
echo "=========================================================="

TARGETS=(
    "startplasma-x11"
    "plasmashell"
    "kwin_x11"
    "kded5"
    "krunner"
    "kactivitymanagerd"
    "kglobalaccel5"
    "klauncher"
    "kscreen_backend_launcher"
    "plasma-browser-integration-host"
    "xfce4-session"
    "xfwm4"
    "xfce4-panel"
    "xfdesktop"
    "xfsettingsd"
    "xfconfd"
    "xiccd"
    "light-locker"
    "gnome-session"
    "gnome-session-binary"
    "gnome-shell"
    "Xephyr"
)

# Phase 1: Graceful SIGTERM
for proc in "${TARGETS[@]}"; do
    if pgrep -u "$USER_ID" -x "$proc" >/dev/null 2>&1; then
        echo "Sending SIGTERM to $proc..."
        pkill -u "$USER_ID" -TERM -x "$proc" 2>/dev/null || true
    fi
done

sleep 1.5

# Phase 2: Forceful SIGKILL for any stubborn lingering processes
for proc in "${TARGETS[@]}"; do
    if pgrep -u "$USER_ID" -x "$proc" >/dev/null 2>&1; then
        echo "Forcing SIGKILL to $proc..."
        pkill -u "$USER_ID" -KILL -x "$proc" 2>/dev/null || true
    fi
done

# Clean up socket and lock files
echo "Cleaning up X1 socket and lock..."
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1

echo "Authentic Linux Desktop stopped successfully."