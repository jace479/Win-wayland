#!/usr/bin/env bash
set -Eeuo pipefail

script="$(dirname "$0")/weston-bridge.sh"
grep -q -- '--backend=x11-backend.so' "$script"
grep -q -- '--socket=' "$script"
grep -q -- 'NT_PLASMA_START_PLASMASHELL' "$script"
printf '%s\n' 'Weston bridge checks passed.'