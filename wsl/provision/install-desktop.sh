#!/usr/bin/env bash
# install-desktop.sh — Modular desktop environment provisioner for ntKDE / NT-Wayland on WSL2
set -Eeuo pipefail

export DEBIAN_FRONTEND=noninteractive

show_help() {
    cat << 'EOF'
Usage: install-desktop.sh [OPTIONS] [PROFILE]

Installs a full desktop environment into WSL2 optimized for ntKDE / WSLg hosting.
Automatically masks display managers (sddm, lightdm, gdm3) to prevent conflicts with WSLg.

Profiles:
  kubuntu       (Default) Full Kubuntu desktop meta-package (KDE Plasma, Breeze, Dolphin, Konsole, etc.)
  kde-full      Upstream Debian/Ubuntu kde-full complete KDE suite
  kde-standard  Standard KDE desktop suite
  xubuntu       Xubuntu / XFCE desktop environment
  ubuntu        Standard Ubuntu GNOME desktop environment

Options:
  --profile <name>  Select desktop profile (alternative to positional argument)
  --minimal         Install minimal packages without recommended extras
  --dry-run         Print actions without modifying system
  -h, --help        Show this help message
EOF
}

PROFILE="kubuntu"
MINIMAL=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        kubuntu|kde-full|kde-standard|xubuntu|ubuntu|xfce|gnome)
            PROFILE="$1"
            shift
            ;;
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --minimal)
            MINIMAL=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            printf 'Error: Unknown option or profile: %s\n' "$1" >&2
            show_help
            exit 1
            ;;
    esac
done

# Normalize profile aliases
case "$PROFILE" in
    xfce) PROFILE="xubuntu" ;;
    gnome) PROFILE="ubuntu" ;;
esac

printf '[ntKDE] Desktop Provisioner: Profile "%s" selected.\n' "$PROFILE"

# Common bridge support packages required by ntKDE IPC and rendering
COMMON_PACKAGES=(
    dbus-x11
    libx11-6
    libxtst6
    x11-utils
    python3-pyqt5
    fonts-noto-color-emoji
    fonts-hack
)

DE_PACKAGES=()
case "$PROFILE" in
    kubuntu)
        if [[ "$MINIMAL" -eq 1 ]]; then
            DE_PACKAGES=(plasma-desktop plasma-workspace breeze-icon-theme)
        else
            DE_PACKAGES=(kubuntu-desktop)
        fi
        ;;
    kde-full)
        DE_PACKAGES=(kde-full)
        ;;
    kde-standard)
        DE_PACKAGES=(kde-standard breeze-icon-theme)
        ;;
    xubuntu)
        if [[ "$MINIMAL" -eq 1 ]]; then
            DE_PACKAGES=(xfwm4 xfce4-panel xfce4-session)
        else
            DE_PACKAGES=(xubuntu-desktop)
        fi
        ;;
    ubuntu)
        if [[ "$MINIMAL" -eq 1 ]]; then
            DE_PACKAGES=(gnome-shell gnome-terminal)
        else
            DE_PACKAGES=(ubuntu-desktop)
        fi
        ;;
    *)
        printf 'Error: Unsupported profile: %s\n' "$PROFILE" >&2
        exit 1
        ;;
esac

ALL_PACKAGES=("${DE_PACKAGES[@]}" "${COMMON_PACKAGES[@]}")

if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[ntKDE] [DRY RUN] Target packages to install:\n'
    for pkg in "${ALL_PACKAGES[@]}"; do
        printf '  - %s\n' "$pkg"
    done
    printf '[ntKDE] [DRY RUN] Display managers to mask: sddm, lightdm, gdm3\n'
    exit 0
fi

printf '[ntKDE] Updating apt package lists...\n'
sudo apt-get update

printf '[ntKDE] Installing desktop profile packages...\n'
if [[ "$MINIMAL" -eq 1 ]]; then
    sudo apt-get install -y --no-install-recommends "${ALL_PACKAGES[@]}"
else
    sudo apt-get install -y "${ALL_PACKAGES[@]}"
fi

# Mask display managers
for dm in sddm lightdm gdm3; do
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files "${dm}.service" >/dev/null 2>&1; then
        printf '[ntKDE] Disabling and masking %s.service...\n' "$dm"
        sudo systemctl disable --now "${dm}.service" 2>/dev/null || true
        sudo systemctl mask "${dm}.service" 2>/dev/null || true
    fi
done

printf '[ntKDE] Installation of %s profile completed successfully.\n' "$PROFILE"
printf '[ntKDE] Run wsl/provision/03-validate-wslg.sh to verify WSLg environment.\n'
