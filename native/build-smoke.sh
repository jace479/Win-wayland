#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
bash native/build-protocol.sh
cc -std=c11 -Wall -Wextra -Werror \
    native/protocol-smoke.c \
    native/build/generated/nt-plasma-foreign-surface-protocol.c \
    -I native/build/generated \
    $(pkg-config --cflags --libs wayland-client wayland-server) \
    -o native/build/nt-plasma-protocol-smoke
native/build/nt-plasma-protocol-smoke