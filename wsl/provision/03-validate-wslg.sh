#!/usr/bin/env bash
set -Eeuo pipefail

required=(DISPLAY WAYLAND_DISPLAY PULSE_SERVER)
for variable in "${required[@]}"; do
    if [[ -z "${!variable:-}" ]]; then
        printf 'Missing WSLg environment variable: %s\n' "$variable" >&2
        exit 1
    fi
done

command -v dbus-run-session >/dev/null
printf '%s\n' "WSLg environment is available. Test a simple GUI application before Plasma."
