#!/usr/bin/env bash
target="${1:-.}"
if [[ "$target" =~ ^https?:// ]]; then
    /mnt/c/Windows/System32/cmd.exe /c start "WSL" "$target" >/dev/null 2>&1 &
else
    win_path="$(wslpath -w "$target" 2>/dev/null || echo "$target")"
    /mnt/c/Windows/System32/cmd.exe /c start "WSL" "$win_path" >/dev/null 2>&1 &
fi
