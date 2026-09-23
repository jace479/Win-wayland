#!/usr/bin/env bash
set -Eeuo pipefail

log_dir="${XDG_STATE_HOME:-$HOME/.local/state}/nt-plasma"
mkdir -p "$log_dir"
log_file="$log_dir/plasma.log"
exec >>"$log_file" 2>&1

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
    printf '%s\n' "WSLg display variables are unavailable; refusing to start Plasma." >&2
    exit 1
fi

if pgrep -u "$(id -u)" -x plasmashell >/dev/null 2>&1; then
    printf '%s\n' "A Plasma shell is already running."
    exit 0
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -x "$script_dir/sync-windows-drives-to-dolphin.sh" ]]; then
    bash "$script_dir/sync-windows-drives-to-dolphin.sh" || true
fi

if command -v startplasma-wayland >/dev/null 2>&1 && [[ -e /dev/dri/renderD128 ]]; then
    exec dbus-run-session -- startplasma-wayland
fi

if command -v startplasma-wayland >/dev/null 2>&1 && [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
    printf '%s\n' "Plasma Wayland is unavailable: WSLg does not expose a KWin DRM render node; using X11." >&2
fi

if command -v startplasma-x11 >/dev/null 2>&1; then
    exec dbus-run-session -- startplasma-x11
fi

if command -v plasmashell >/dev/null 2>&1; then
    printf '%s\n' "startplasma launcher not found; starting plasmashell and krunner directly."
    exec dbus-run-session -- bash -c '
        command -v kwin_x11 >/dev/null 2>&1 && kwin_x11 --replace &
        krunner &
        exec plasmashell --no-respawn
    '
fi

printf '%s\n' "No Plasma session launcher was found." >&2
exit 1

