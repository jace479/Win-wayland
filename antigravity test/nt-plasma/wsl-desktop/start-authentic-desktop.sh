#!/usr/bin/env bash
set -eo pipefail

SESSION="${1:-plasma}"
WIDTH="${2:-1920}"
HEIGHT="${3:-1080}"

case "$SESSION" in
    plasma)
        SESSION_NAME="Plasma"
        ;;
    xfce)
        SESSION_NAME="XFCE"
        ;;
    gnome)
        SESSION_NAME="GNOME"
        ;;
    *)
        SESSION_NAME="$SESSION"
        ;;
esac

echo "=========================================================="
echo "Starting Authentic Linux Desktop: ${SESSION_NAME} (${WIDTH}x${HEIGHT})"
echo "Native WSLg UNIX Domain Sockets - Strictly ZERO TCP/IP"
echo "=========================================================="

# Cleanup handler for early exit / signals
cleanup() {
    local exit_code=$?
    trap - EXIT INT TERM
    echo "Caught exit/signal - cleaning up child processes and sockets..."
    if [ -n "${XEPHYR_PID:-}" ] && kill -0 "$XEPHYR_PID" 2>/dev/null; then
        kill "$XEPHYR_PID" 2>/dev/null || true
    fi
    rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
    exit "$exit_code"
}
trap cleanup EXIT INT TERM

# Ensure /tmp/.X11-unix is rw and mode 1777 (WSLg mounts it ro by default)
sudo mount -o remount,rw /tmp/.X11-unix 2>/dev/null || true
sudo chmod 1777 /mnt/wslg/.X11-unix 2>/dev/null || true
sudo chmod 1777 /tmp/.X11-unix 2>/dev/null || true

# Remove stale lock/socket if no active Xephyr process
if ! pgrep -x Xephyr >/dev/null 2>&1; then
    rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
fi

# Export native WSLg display variables
export WAYLAND_DISPLAY=wayland-0
export DISPLAY=:0
export PULSE_SERVER="unix:/mnt/wslg/PulseServer"

# Launch Xephyr nested X server with GLAMOR acceleration on display :1
echo "Launching Xephyr nested display :1 (${WIDTH}x${HEIGHT}) with GLAMOR..."
Xephyr -ac -br -noreset -resizeable -glamor -screen "${WIDTH}x${HEIGHT}" -title "Authentic Linux Desktop - ${SESSION_NAME}" :1 >/tmp/xephyr.log 2>&1 &
XEPHYR_PID=$!

# Wait for UNIX socket /tmp/.X11-unix/X1 to appear
echo "Waiting for /tmp/.X11-unix/X1 socket to appear..."
for i in $(seq 1 50); do
    if [ -S /tmp/.X11-unix/X1 ]; then
        echo "Display :1 UNIX domain socket is ready!"
        break
    fi
    sleep 0.1
done

if [ ! -S /tmp/.X11-unix/X1 ]; then
    echo "ERROR: Xephyr failed to create socket /tmp/.X11-unix/X1" >&2
    cat /tmp/xephyr.log >&2
    exit 1
fi

# Launch requested desktop session
case "$SESSION" in
    plasma)
        echo "Launching KDE Plasma session on display :1..."
        export DISPLAY=:1
        export DESKTOP_SESSION=plasma
        export XDG_CURRENT_DESKTOP=KDE
        export XDG_SESSION_DESKTOP=KDE
        export KDE_FULL_SESSION=true
        # Ensure kactivitymanagerd is started if needed
        if [ -x /usr/lib/x86_64-linux-gnu/libexec/kactivitymanagerd ]; then
            /usr/lib/x86_64-linux-gnu/libexec/kactivitymanagerd >/tmp/kactivity.log 2>&1 &
        fi
        exec startplasma-x11
        ;;
    xfce)
        echo "Launching XFCE desktop session on display :1..."
        export DISPLAY=:1
        export DESKTOP_SESSION=xfce
        export XDG_CURRENT_DESKTOP=XFCE
        exec xfce4-session
        ;;
    gnome)
        echo "Launching GNOME session on display :1..."
        export DISPLAY=:1
        export DESKTOP_SESSION=gnome
        export XDG_CURRENT_DESKTOP=GNOME
        export XDG_SESSION_DESKTOP=GNOME
        exec gnome-session
        ;;
    *)
        echo "Unknown session type: $SESSION" >&2
        echo "Available options: plasma, xfce, gnome" >&2
        exit 1
        ;;
esac