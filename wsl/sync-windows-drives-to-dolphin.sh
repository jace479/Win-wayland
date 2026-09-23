#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$script_dir/sync-windows-drives-to-dolphin.py" "${1:-$HOME/.local/share/user-places.xbel}" "${2:-/mnt}"