#!/usr/bin/env bash
# 02-install-kde-plasma.sh — Installs full Kubuntu Desktop / KDE Plasma on WSL2
set -Eeuo pipefail

export DEBIAN_FRONTEND=noninteractive

TARGET_PROFILE="kubuntu"
MINIMAL=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --minimal)
            MINIMAL=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        *)
            shift
            ;;
    esac
done

printf '[ntKDE] Preparing to install desktop environment in WSL...\n'

# Detect distro
DISTRO_ID="ubuntu"
if [[ -f /etc/os-release ]]; then
    # shellcheck source=/dev/null
    source /etc/os-release
    DISTRO_ID="${ID:-ubuntu}"
fi

# Define packages based on distro and profile
PACKAGES=()
if [[ "$MINIMAL" -eq 1 ]]; then
    printf '[ntKDE] Minimal mode requested. Installing core plasma-desktop only.\n'
    PACKAGES=(plasma-desktop plasma-workspace dbus-x11 libx11-6 libxtst6 x11-utils python3-pyqt5 breeze-icon-theme)
else
    printf '[ntKDE] Full desktop mode requested. Target: kubuntu-desktop.\n'
    if [[ "$DISTRO_ID" == "ubuntu" ]]; then
        PACKAGES=(kubuntu-desktop dbus-x11 libx11-6 libxtst6 x11-utils python3-pyqt5)
    else
        # Debian or other Debian-derivatives
        PACKAGES=(kde-standard dbus-x11 libx11-6 libxtst6 x11-utils python3-pyqt5 breeze-icon-theme)
    fi
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[ntKDE] [DRY RUN] Would update apt and install: %s\n' "${PACKAGES[*]}"
    printf '[ntKDE] [DRY RUN] Would mask display managers (sddm, lightdm, gdm3)\n'
    exit 0
fi

printf '[ntKDE] Updating package lists...\n'
sudo apt-get update

printf '[ntKDE] Installing packages: %s\n' "${PACKAGES[*]}"
sudo apt-get install -y "${PACKAGES[@]}"

# Disable & mask all display managers to prevent conflict with WSLg
for dm in sddm lightdm gdm3; do
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files "${dm}.service" >/dev/null 2>&1; then
        printf '[ntKDE] Disabling and masking %s.service...\n' "$dm"
        sudo systemctl disable --now "${dm}.service" 2>/dev/null || true
        sudo systemctl mask "${dm}.service" 2>/dev/null || true
    fi
done

printf '[ntKDE] Desktop installation complete. WSLg smoke testing must pass before launching Plasma.\n'
