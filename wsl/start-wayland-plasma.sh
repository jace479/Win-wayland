#!/usr/bin/env bash
# ==============================================================================
# ntKDE Wayland Desktop Surface Launcher
# ==============================================================================
# Launches an authentic KDE Plasma 6 Wayland session via kwin_wayland
# nested over WSLg's outer Wayland display (wayland-0).
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

LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/nt-plasma"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/wayland-plasma.log"

printf '%s [ntKDE] Starting Wayland Plasma Desktop (%sx%s)\n' \
    "$(date -Iseconds)" "$WIDTH" "$HEIGHT" >"$LOG_FILE"

# Ensure user runtime directory with standard 0700 permissions (required by DBus)
RUNTIME_DIR="/run/user/$USER_ID"
if [[ ! -d "$RUNTIME_DIR" ]]; then
    mkdir -p -m 0700 "$RUNTIME_DIR" 2>/dev/null || RUNTIME_DIR="/tmp/runtime-$USER_ID"
    mkdir -p -m 0700 "$RUNTIME_DIR"
fi
export XDG_RUNTIME_DIR="$RUNTIME_DIR"

# Link WSLg outer Wayland socket into user runtime directory
if [[ -S "/mnt/wslg/runtime-dir/wayland-0" && ! -S "$XDG_RUNTIME_DIR/wayland-0" ]]; then
    ln -sfn "/mnt/wslg/runtime-dir/wayland-0" "$XDG_RUNTIME_DIR/wayland-0"
fi

export WAYLAND_DISPLAY="wayland-0"
export PULSE_SERVER="unix:/mnt/wslg/PulseServer"

# Internal Wayland socket for Plasma session
INTERNAL_WAYLAND="wayland-ntkde"
rm -f "$XDG_RUNTIME_DIR/$INTERNAL_WAYLAND" "$XDG_RUNTIME_DIR/$INTERNAL_WAYLAND.lock"

# Session environment
export DESKTOP_SESSION=plasma
export XDG_CURRENT_DESKTOP="KDE"
export XDG_SESSION_DESKTOP="KDE"
export KDE_FULL_SESSION=true
export QT_QPA_PLATFORM=wayland

# Sync Windows drives to Dolphin places
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$script_dir/sync-windows-drives-to-dolphin.sh" ]]; then
    bash "$script_dir/sync-windows-drives-to-dolphin.sh" >>"$LOG_FILE" 2>&1 || true
fi

printf '%s [ntKDE] Launching kwin_wayland nested compositor (%sx%s)...\n' "$(date -Iseconds)" "$WIDTH" "$HEIGHT" >>"$LOG_FILE"

# 1. Start kwin_wayland as nested compositor over WSLg wayland-0
kwin_wayland \
    --wayland-display wayland-0 \
    --socket "$INTERNAL_WAYLAND" \
    --width "$WIDTH" \
    --height "$HEIGHT" \
    --no-lockscreen \
    >>"$LOG_FILE" 2>&1 &
KWIN_PID=$!

cleanup() {
    printf '%s [ntKDE] Cleaning up Wayland Plasma session...\n' "$(date -Iseconds)" >>"$LOG_FILE"
    kill "$KWIN_PID" 2>/dev/null || true
    rm -f "$XDG_RUNTIME_DIR/$INTERNAL_WAYLAND" "$XDG_RUNTIME_DIR/$INTERNAL_WAYLAND.lock"
}
trap cleanup EXIT INT TERM

# 2. Wait for internal Wayland socket to appear
for _ in {1..50}; do
    if [[ -S "$XDG_RUNTIME_DIR/$INTERNAL_WAYLAND" ]]; then
        break
    fi
    sleep 0.1
done

if [[ ! -S "$XDG_RUNTIME_DIR/$INTERNAL_WAYLAND" ]]; then
    printf '%s [ntKDE] ERROR: kwin_wayland failed to create socket %s\n' "$(date -Iseconds)" "$INTERNAL_WAYLAND" >>"$LOG_FILE"
    exit 1
fi

printf '%s [ntKDE] Internal Wayland socket %s is ready. Spawning plasmashell...\n' "$(date -Iseconds)" "$INTERNAL_WAYLAND" >>"$LOG_FILE"

# 3. Connect client applications to the nested Wayland compositor
export WAYLAND_DISPLAY="$INTERNAL_WAYLAND"

# 4. Start plasmashell
plasmashell --no-respawn >>"$LOG_FILE" 2>&1 &
PLASMA_PID=$!

wait "$KWIN_PID"
