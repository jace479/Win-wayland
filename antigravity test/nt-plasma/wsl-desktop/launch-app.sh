#!/usr/bin/env bash
set -Eeuo pipefail

app="${1:-}"
shift || true

if [ -z "$app" ]; then
    echo "Usage: $0 <app-name> [args...]" >&2
    exit 1
fi

log_dir="${XDG_STATE_HOME:-$HOME/.local/state}/nt-plasma"
mkdir -p "$log_dir"
log_file="$log_dir/app-launch.log"

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

echo "[$(date "+%Y-%m-%d %H:%M:%S")] Launching application: $app (args: $*)" >>"$log_file"

case "$app" in
    dolphin)
        target="${1:-}"
        if [ -n "$target" ]; then
            linux_path="$(wslpath -u "$target" 2>/dev/null || echo "$target")"
            nohup dolphin "$linux_path" </dev/null >>"$log_file" 2>&1 &
        else
            nohup dolphin </dev/null >>"$log_file" 2>&1 &
        fi
        ;;
    konsole)
        target="${1:-}"
        if [ -n "$target" ]; then
            linux_path="$(wslpath -u "$target" 2>/dev/null || echo "$target")"
            nohup konsole --workdir "$linux_path" </dev/null >>"$log_file" 2>&1 &
        else
            nohup konsole </dev/null >>"$log_file" 2>&1 &
        fi
        ;;
    systemsettings)
        nohup systemsettings "$@" </dev/null >>"$log_file" 2>&1 &
        ;;
    kate)
        nohup kate "$@" </dev/null >>"$log_file" 2>&1 &
        ;;
    krunner)
        if ! pgrep -u "$USER_ID" -x krunner >/dev/null 2>&1; then
            nohup krunner </dev/null >>"$log_file" 2>&1 &
        else
            qdbus org.kde.krunner /App display >>"$log_file" 2>&1 || nohup krunner </dev/null >>"$log_file" 2>&1 &
        fi
        ;;
    *)
        nohup "$app" "$@" </dev/null >>"$log_file" 2>&1 &
        ;;
esac

disown -a 2>/dev/null || true
echo "[$(date "+%Y-%m-%d %H:%M:%S")] Application $app started detached." >>"$log_file"

