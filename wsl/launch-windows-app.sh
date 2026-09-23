#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 1 || -z "$1" ]]; then
    printf '%s\n' 'Usage: launch-windows-app.sh <application-id>' >&2
    exit 2
fi

# If argument is a direct file path (e.g. .exe, .msi, .bat, .cmd)
target_path="$1"
if [[ -e "$target_path" || "$target_path" == /* || "$target_path" == [A-Za-z]:* ]]; then
    # If path is inside WSL Linux filesystem, copy or resolve, but if on DrvFs (/mnt/...)
    if [[ "$target_path" == /mnt/* ]]; then
        win_target="$(wslpath -w "$target_path")"
    elif [[ -f "$target_path" ]]; then
        # File is on Linux filesystem, copy to temp Windows folder so Windows can execute it
        win_temp="/mnt/c/Users/${USER:-Public}/AppData/Local/Temp/ntkde_launch"
        mkdir -p "$win_temp"
        cp -f "$target_path" "$win_temp/"
        fname="$(basename "$target_path")"
        win_target="$(wslpath -w "$win_temp/$fname")"
    else
        win_target="$target_path"
    fi
    exec /mnt/c/Windows/System32/cmd.exe /c start "" "$win_target"
fi

catalog_path="${NT_PLASMA_WINDOWS_CATALOG:-$HOME/.local/share/nt-plasma/windows-catalog.json}"
host_script_path="${NT_PLASMA_HOST_SCRIPT:-$(dirname "$catalog_path")/Start-WindowsCatalogApplication.ps1}"
host_script="$(wslpath -w "$host_script_path")"
host_catalog="$(wslpath -w "$catalog_path")"

exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$host_script" \
    -CatalogPath "$host_catalog" -ApplicationId "$1"