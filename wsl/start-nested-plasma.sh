#!/usr/bin/env bash
# ==============================================================================
# ntKDE Single Desktop Surface Launcher (Plasma 6 Wayland)
# ==============================================================================
# Launches an authentic KDE Plasma 6 session inside a nested KWin Wayland
# compositor presented to Windows NT via WSLg.
# ==============================================================================

set -Eeuo pipefail

# Sanitize environment from Windows variable leakage
if [[ "${HOME:-}" == *":"* ]] || [[ ! -d "${HOME:-}" ]]; then
    export HOME="$(getent passwd "$(id -u)" | cut -d: -f6)"
fi
export USER="$(id -un)"
export USER_ID="$(id -u)"

WIDTH="${1:-${NT_KDE_WIDTH:-1920}}"
HEIGHT="${2:-${NT_KDE_HEIGHT:-1080}}"
SOCKET_NAME="${NT_PLASMA_WAYLAND_SOCKET:-nt-plasma-kwin}"

LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/nt-plasma"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/nested-plasma.log"

printf '%s [ntKDE] Starting Nested KDE Plasma 6 Desktop (%sx%s)\n' \
    "$(date -Iseconds)" "$WIDTH" "$HEIGHT" >"$LOG_FILE"

# 1. Setup XDG runtime directory and D-Bus session bus
RUNTIME_DIR="/run/user/$USER_ID"
if [[ ! -d "$RUNTIME_DIR" ]]; then
    mkdir -p -m 0700 "$RUNTIME_DIR" 2>/dev/null || RUNTIME_DIR="/tmp/runtime-$USER_ID"
    mkdir -p -m 0700 "$RUNTIME_DIR"
fi
export XDG_RUNTIME_DIR="$RUNTIME_DIR"

if [[ -S "/mnt/wslg/runtime-dir/wayland-0" && ! -S "$XDG_RUNTIME_DIR/wayland-0" ]]; then
    ln -sfn "/mnt/wslg/runtime-dir/wayland-0" "$XDG_RUNTIME_DIR/wayland-0"
fi

if [[ -S "$XDG_RUNTIME_DIR/bus" ]]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
fi

# 2. Cleanup stale socket and lock files
rm -f "$XDG_RUNTIME_DIR/$SOCKET_NAME" "$XDG_RUNTIME_DIR/$SOCKET_NAME.lock"

# 3. Export KDE Plasma session environment
export DISPLAY="${DISPLAY:-:0}"
export DESKTOP_SESSION=plasma
export XDG_CURRENT_DESKTOP="KDE"
export XDG_SESSION_DESKTOP="KDE"
export KDE_FULL_SESSION=true
export XDG_MENU_PREFIX="plasma-"
export PULSE_SERVER="unix:/mnt/wslg/PulseServer"

# 4. Ensure activity manager daemon (kactivitymanagerd) is active in headless mode
# Plasmashell strictly requires kactivitymanagerd to load panels and taskbars.
if ! pgrep -u "$USER_ID" -x kactivitymanagerd >/dev/null 2>&1; then
    if [ -x /usr/lib/x86_64-linux-gnu/libexec/kactivitymanagerd ]; then
        printf '%s [ntKDE] Launching headless kactivitymanagerd...\n' "$(date -Iseconds)" >>"$LOG_FILE"
        QT_QPA_PLATFORM=offscreen /usr/lib/x86_64-linux-gnu/libexec/kactivitymanagerd >>"$LOG_FILE" 2>&1 &
        sleep 0.5
    fi
fi

# 5. Sync Windows drives to Dolphin places
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$script_dir/sync-windows-drives-to-dolphin.sh" ]]; then
    bash "$script_dir/sync-windows-drives-to-dolphin.sh" >>"$LOG_FILE" 2>&1 || true
fi

# 6. Start KRunner daemon in background
if command -v krunner >/dev/null 2>&1; then
    WAYLAND_DISPLAY="$SOCKET_NAME" QT_QPA_PLATFORM=wayland krunner --daemon >>"$LOG_FILE" 2>&1 &
fi

# 7. Launch KWin Wayland nested over WSLg display with plasmashell child
printf '%s [ntKDE] Launching kwin_wayland on socket %s (%sx%s) with plasmashell...\n' \
    "$(date -Iseconds)" "$SOCKET_NAME" "$WIDTH" "$HEIGHT" >>"$LOG_FILE"

exec kwin_wayland \
    --x11-display :0 \
    --socket "$SOCKET_NAME" \
    --width "$WIDTH" \
    --height "$HEIGHT" \
    --no-lockscreen \
    /usr/bin/plasmashell >>"$LOG_FILE" 2>&1
