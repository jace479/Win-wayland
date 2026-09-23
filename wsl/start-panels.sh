#!/usr/bin/env bash
# ==============================================================================
# ntKDE Panel-Only Launcher (WSLg Native Mode)
# ==============================================================================
# Launches KDE Plasma panels directly on WSLg (:0) without Xephyr.
# Starts kscreen_backend_launcher with XRandR so Display Settings work.
# Docks panels reliably via XCB / X11 dock protocol.
# ==============================================================================

set -Eeuo pipefail

# Sanitize environment from Windows variable leakage
if [[ "${HOME:-}" == *":"* ]] || [[ ! -d "${HOME:-}" ]]; then
    export HOME="$(getent passwd "$(id -u)" | cut -d: -f6)"
fi
export USER="$(id -un)"
export USER_ID="$(id -u)"

LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/nt-plasma"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/panels.log"

printf '%s [ntKDE] Starting KDE Panels (WSLg native mode)\n' \
    "$(date -Iseconds)" >"$LOG_FILE"

# 1. Force XCB (X11) backend so panels export as X11 DOCK windows
# WSLg Weston does NOT support Wayland layer-shell protocol!
export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export PULSE_SERVER="unix:/mnt/wslg/PulseServer"
export XDG_RUNTIME_DIR="/run/user/$USER_ID"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"

export QT_QPA_PLATFORM="xcb"
export KSCREEN_BACKEND="XRandR"
export DESKTOP_SESSION=plasma
export XDG_CURRENT_DESKTOP="KDE"
export XDG_SESSION_DESKTOP="KDE"
export KDE_FULL_SESSION=true
export QML_XHR_ALLOW_FILE_READ=1
export PW_LOG_LEVEL=0
export PIPEWIRE_DEBUG=0
export QT_LOGGING_RULES="*.debug=false;kpipewire_logging.warning=false;pw.conf.warning=false;org.kde.plasma.libtaskmanager.warning=false"
export XDG_MENU_PREFIX="plasma-"
export XDG_DATA_DIRS="$HOME/.local/share:/usr/local/share:/usr/share:/var/lib/snapd/desktop:/var/lib/flatpak/exports/share:$HOME/.local/share/flatpak/exports/share"

# Preload ntKDE popup fix library so applet popups (Kickoff, menus)
# use override_redirect=1 under WSLg Weston/Xwayland to prevent window manager misplacement
POPUP_FIX_SRC="/mnt/d/WinKDE/wsl/libntkde_popup_fix.c"
POPUP_FIX_LIB="$HOME/.local/lib/libntkde_popup_fix.so"
if [[ -f "$POPUP_FIX_SRC" ]]; then
    mkdir -p "$HOME/.local/lib"
    if [[ ! -f "$POPUP_FIX_LIB" || "$POPUP_FIX_SRC" -nt "$POPUP_FIX_LIB" ]]; then
        gcc -shared -fPIC -O2 "$POPUP_FIX_SRC" -o "$POPUP_FIX_LIB" -lxcb -lX11 -ldl -lpthread 2>/dev/null || true
    fi
    if [[ -f "$POPUP_FIX_LIB" ]]; then
        export LD_PRELOAD="$POPUP_FIX_LIB${LD_PRELOAD:+:$LD_PRELOAD}"
    fi
fi

# Import environment to systemd user session so background daemons have DISPLAY & XCB
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS QT_QPA_PLATFORM DESKTOP_SESSION XDG_CURRENT_DESKTOP KDE_FULL_SESSION KSCREEN_BACKEND XDG_DATA_DIRS XDG_MENU_PREFIX LD_PRELOAD 2>/dev/null || true

# 2. Cleanup old instances
pkill -x Xephyr 2>/dev/null || true
pkill -x plasmashell 2>/dev/null || true
pkill -x kwin_x11 2>/dev/null || true
pkill -f "kscreen_backend_launcher" 2>/dev/null || true
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1

sleep 0.5

# 3. Ensure D-Bus session is available
if ! pgrep -x dbus-daemon >/dev/null 2>&1; then
    eval "$(dbus-launch --sh-syntax)" 2>>"$LOG_FILE" || true
fi
mkdir -p "$LOG_DIR"
cat <<EOF > "$LOG_DIR/dbus.env"
export DBUS_SESSION_BUS_ADDRESS='${DBUS_SESSION_BUS_ADDRESS:-}'
export DBUS_SESSION_BUS_PID='${DBUS_SESSION_BUS_PID:-}'
EOF

# 4. Start KScreen backend launcher with XRandR (Fixes "kscreen is not available")
if [ -x /usr/lib/x86_64-linux-gnu/libexec/kf6/kscreen_backend_launcher ]; then
    printf '%s [ntKDE] Starting KScreen XRandR backend daemon (KF6)...\n' "$(date -Iseconds)" >>"$LOG_FILE"
    KSCREEN_BACKEND=XRandR QT_QPA_PLATFORM=xcb /usr/lib/x86_64-linux-gnu/libexec/kf6/kscreen_backend_launcher >>"$LOG_FILE" 2>&1 &
elif [ -x /usr/lib/x86_64-linux-gnu/libexec/kf5/kscreen_backend_launcher ]; then
    printf '%s [ntKDE] Starting KScreen XRandR backend daemon (KF5)...\n' "$(date -Iseconds)" >>"$LOG_FILE"
    /usr/lib/x86_64-linux-gnu/libexec/kf5/kscreen_backend_launcher XRandR >>"$LOG_FILE" 2>&1 &
fi

# 5. Start kactivitymanagerd if available (plasmashell dependency)
if [ -x /usr/lib/x86_64-linux-gnu/libexec/kactivitymanagerd ]; then
    /usr/lib/x86_64-linux-gnu/libexec/kactivitymanagerd >>"$LOG_FILE" 2>&1 &
fi

# 5b. Start krunner in background for instant Alt+Space activation
if command -v krunner >/dev/null 2>&1; then
    krunner --replace >>"$LOG_FILE" 2>&1 &
fi

# 6. Ensure WSLg multi-monitor topology is active and designate primary display
# WSLg Xwayland starts at 640x480 until queried; querying activates all monitors
xrandr --query >/dev/null 2>&1 || true
sleep 1
# Set rdp-0 (Windows primary monitor) as X11 primary so Plasma and popups anchor to it
xrandr --output rdp-0 --primary >/dev/null 2>&1 || true

# 7. Sync Windows drives to Dolphin places
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$script_dir/sync-windows-drives-to-dolphin.sh" ]]; then
    bash "$script_dir/sync-windows-drives-to-dolphin.sh" >>"$LOG_FILE" 2>&1 || true
fi

# 7b. Configure default panel to use native org.kde.plasma.icontasks (Icons-Only Task Manager)
if [[ -f "$script_dir/configure_default_panel.py" ]]; then
    python3 "$script_dir/configure_default_panel.py" >>"$LOG_FILE" 2>&1 || true
fi

# 7c. Ensure XDG menu definitions exist for Kickoff application launcher
mkdir -p "$HOME/.config/menus"
if [[ -f /etc/xdg/menus/plasma-applications.menu ]]; then
    ln -sf /etc/xdg/menus/plasma-applications.menu "$HOME/.config/menus/applications.menu"
    ln -sf /etc/xdg/menus/plasma-applications.menu "$HOME/.config/menus/plasma-applications.menu"
fi

# 7d. Start winget proxy daemon for Discover Windows app integration
if [[ -f "$script_dir/winget-proxy.py" ]]; then
    pkill -f "winget-proxy.py" 2>/dev/null || true
    python3 "$script_dir/winget-proxy.py" >>"$LOG_DIR/winget-proxy.log" 2>&1 &
fi

# Ensure menu configuration is up-to-date
if [[ -f "$script_dir/ensure-plasma-menu.py" ]]; then
    python3 "$script_dir/ensure-plasma-menu.py" >>"$LOG_FILE" 2>&1 || true
fi

# Rebuild sycoca in background so Kickoff and KRunner see all Windows + Linux apps immediately
if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 --noincremental >>"$LOG_FILE" 2>&1 &
fi

# 7e. Sync KDE wallpaper to Windows host desktop
if [[ -f "/mnt/d/WinKDE/powershell/Sync-KdeWallpaper.ps1" ]]; then
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\WinKDE\powershell\Sync-KdeWallpaper.ps1' >/dev/null 2>&1 &
fi

printf '%s [ntKDE] Launching plasmashell on WSLg display %s (xcb mode)...\n' \
    "$(date -Iseconds)" "$DISPLAY" >>"$LOG_FILE"

# 8. Launch plasmashell with supervised restart loop
# Automatically restarts on crash with exponential backoff (2s, 4s, 6s, 8s, 10s).
# Stops on clean exit (code 0) or SIGTERM (code 143).
# Re-applies panel configuration after each restart.
MAX_PLASMA_RESTARTS=5

configure_panels() {
    # Wait for Plasma DBus service to become available
    for _ in {1..40}; do
        if gdbus call --session --dest org.kde.plasmashell --object-path /PlasmaShell --method org.freedesktop.DBus.Peer.Ping >/dev/null 2>&1; then
            break
        fi
        sleep 0.25
    done

    # Ensure a bottom panel exists with kickoff, tasks, system tray, and clock
    local sdir
    sdir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ -f "$sdir/eval_plasma.py" && -f "$sdir/ensure-panel.js" ]]; then
        python3 "$sdir/eval_plasma.py" "$sdir/ensure-panel.js" >>"$LOG_FILE" 2>&1 || true
    fi
}

if command -v plasmashell >/dev/null 2>&1; then
    plasma_restart_count=0

    while [ "$plasma_restart_count" -lt "$MAX_PLASMA_RESTARTS" ]; do
        printf '%s [ntKDE] Starting plasmashell (attempt %d/%d)...\n' \
            "$(date -Iseconds)" "$((plasma_restart_count + 1))" "$MAX_PLASMA_RESTARTS" >>"$LOG_FILE"

        # Launch plasmashell in background, configure panels, then wait
        plasmashell --no-respawn >>"$LOG_FILE" 2>&1 &
        PLASMA_PID=$!

        # Configure panels in background (non-blocking)
        configure_panels &

        # Wait for plasmashell to exit
        wait "$PLASMA_PID"
        exit_code=$?

        plasma_restart_count=$((plasma_restart_count + 1))

        printf '%s [ntKDE] plasmashell exited (code %d), restart count: %d/%d\n' \
            "$(date -Iseconds)" "$exit_code" "$plasma_restart_count" "$MAX_PLASMA_RESTARTS" >>"$LOG_FILE"

        # Don't restart on clean shutdown (exit 0) or SIGTERM (143)
        if [ "$exit_code" -eq 0 ] || [ "$exit_code" -eq 143 ]; then
            printf '%s [ntKDE] plasmashell exited cleanly. Not restarting.\n' \
                "$(date -Iseconds)" >>"$LOG_FILE"
            break
        fi

        # Don't restart if we've hit the limit
        if [ "$plasma_restart_count" -ge "$MAX_PLASMA_RESTARTS" ]; then
            printf '%s [ntKDE] ERROR: plasmashell exceeded max restarts (%d). Giving up.\n' \
                "$(date -Iseconds)" "$MAX_PLASMA_RESTARTS" >>"$LOG_FILE"
            break
        fi

        # Exponential backoff: 2s, 4s, 6s, 8s, 10s
        backoff_secs=$((plasma_restart_count * 2))
        printf '%s [ntKDE] Restarting plasmashell in %ds...\n' \
            "$(date -Iseconds)" "$backoff_secs" >>"$LOG_FILE"
        sleep "$backoff_secs"
    done
else
    printf '%s [ntKDE] NOTICE: plasmashell is not installed in WSL. Run provision/02-install-kde-plasma.sh to install Plasma.\n' "$(date -Iseconds)" >>"$LOG_FILE"
    printf '%s [ntKDE] WSLg environment and ntKDE host bridge are ready.\n' "$(date -Iseconds)" >>"$LOG_FILE"
fi
