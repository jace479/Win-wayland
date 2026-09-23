#!/usr/bin/env bash
set -Eeuo pipefail

conf="/etc/wsl.conf"
if [[ ! -f "$conf" ]] || ! grep -q '^systemd=true$' "$conf"; then
    install -m 0644 "$(dirname "$0")/../wsl.conf.template" "$conf"
fi

printf '%s\n' "WSL systemd configuration is present. Restart the distro with: wsl.exe --shutdown"
