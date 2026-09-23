#!/usr/bin/env bash
set -Eeuo pipefail

script="$(dirname "$0")/plasma-launch.sh"
grep -q 'renderD128' "$script"
grep -q 'using X11' "$script"
printf '%s\n' 'Plasma launcher fallback checks passed.'