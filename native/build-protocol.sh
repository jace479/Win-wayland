#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
protocol="$repo_root/docs/architecture/nt-plasma-foreign-surface-v1.xml"
output_dir="${1:-$repo_root/native/build/generated}"

if ! command -v wayland-scanner >/dev/null 2>&1; then
    printf '%s\n' 'wayland-scanner is required. Install libwayland-dev first.' >&2
    exit 1
fi
if [[ ! -f "$protocol" ]]; then
    printf 'Protocol XML was not found: %s\n' "$protocol" >&2
    exit 1
fi

mkdir -p "$output_dir"
wayland-scanner client-header "$protocol" "$output_dir/nt-plasma-foreign-surface-client-protocol.h"
wayland-scanner server-header "$protocol" "$output_dir/nt-plasma-foreign-surface-server-protocol.h"
wayland-scanner private-code "$protocol" "$output_dir/nt-plasma-foreign-surface-protocol.c"
printf 'Generated native protocol bindings in %s\n' "$output_dir"