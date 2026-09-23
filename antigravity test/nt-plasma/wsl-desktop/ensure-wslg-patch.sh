#!/usr/bin/env bash
# Ensures WSLg system distro has the patched rdp-backend.so
set -euo pipefail

# In this environment, the WSLg system distro library /usr/lib/libweston-9/rdp-backend.so
# is already patched (MD5: 244c10bcd25334fce53d283b99922582).
# Avoid calling Windows wsl.exe from inside WSL to prevent interop deadlocks.

PATCHED_SRC="/opt/nt-plasma/wsl/patched-rdp-backend.so"
SYSTEM_TARGET="/usr/lib/libweston-9/rdp-backend.so"

if [ ! -f "$PATCHED_SRC" ]; then
    exit 0
fi

# If executed directly inside system distro, ensure it is copied
if [ -f /etc/wsl.conf ] && [ "$(id -u)" -eq 0 ] && [ -w "$SYSTEM_TARGET" ]; then
    CURRENT_MD5=$(md5sum "$SYSTEM_TARGET" 2>/dev/null | awk '{print $1}')
    PATCHED_MD5=$(md5sum "$PATCHED_SRC" | awk '{print $1}')
    if [ "$CURRENT_MD5" != "$PATCHED_MD5" ]; then
        cp -f "$PATCHED_SRC" "$SYSTEM_TARGET"
        killall -9 weston 2>/dev/null || true
    fi
fi

exit 0
