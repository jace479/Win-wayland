#!/usr/bin/env bash
set -Eeuo pipefail

log_dir="${XDG_STATE_HOME:-$HOME/.local/state}/nt-plasma"
mkdir -p "$log_dir"
log_file="$log_dir/plasma.log"
exec >>"$log_file" 2>&1

now=$(date "+%Y-%m-%d %H:%M:%S")
echo "========================================================"
echo "[$now] Starting KDE Plasma on WSLg (Native Wayland UNIX Socket, ZERO TCP/IP)"
echo "========================================================"

USER_ID="$(id -u)"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$USER_ID}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
export QT_QPA_PLATFORM="wayland;xcb"
export GDK_BACKEND="wayland,x11"
export DESKTOP_SESSION=plasma
export XDG_CURRENT_DESKTOP=KDE
export XDG_SESSION_DESKTOP=KDE
export KDE_FULL_SESSION=true

# 0. Ensure WSLg system distro assertion patch is active
if [ -x /opt/nt-plasma/wsl/ensure-wslg-patch.sh ]; then
    /opt/nt-plasma/wsl/ensure-wslg-patch.sh || true
fi

# 1. Start KDE Daemon (kded5) for themes, fonts, hotkeys
if ! pgrep -u "$USER_ID" -x kded5 >/dev/null 2>&1; then
    echo "[$(date "+%Y-%m-%d %H:%M:%S")] Launching kded5..."
    nohup kded5 </dev/null >>"$log_file" 2>&1 &
fi

# 2. Start KDE Plasma Shell (Taskbar, Kickoff, System Tray)
if ! pgrep -u "$USER_ID" -x plasmashell >/dev/null 2>&1; then
    echo "[$(date "+%Y-%m-%d %H:%M:%S")] Launching plasmashell..."
    nohup plasmashell </dev/null >>"$log_file" 2>&1 &
fi

# 3. Ensure KRunner is active
if ! pgrep -u "$USER_ID" -x krunner >/dev/null 2>&1; then
    echo "[$(date "+%Y-%m-%d %H:%M:%S")] Launching krunner..."
    nohup krunner </dev/null >>"$log_file" 2>&1 &
fi

disown -a 2>/dev/null || true
echo "[$(date "+%Y-%m-%d %H:%M:%S")] KDE Plasma components running smoothly on WSLg via Wayland UNIX socket."
