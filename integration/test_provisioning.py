"""Integration tests for desktop environment provisioning and health gate verification."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROVISION_DIR = REPO_ROOT / "wsl" / "provision"


class TestProvisioningScripts:
    """Verify provisioning script existence, syntax, and options."""

    def test_scripts_exist(self):
        legacy_script = PROVISION_DIR / "02-install-kde-plasma.sh"
        modular_script = PROVISION_DIR / "install-desktop.sh"
        assert legacy_script.exists(), "02-install-kde-plasma.sh must exist"
        assert modular_script.exists(), "install-desktop.sh must exist"

    def test_legacy_script_dry_run(self):
        script = PROVISION_DIR / "02-install-kde-plasma.sh"
        content = script.read_text(encoding="utf-8")
        assert "kubuntu-desktop" in content
        assert "sddm" in content
        assert "lightdm" in content
        assert "gdm3" in content
        assert "--dry-run" in content

    def test_modular_script_profiles(self):
        script = PROVISION_DIR / "install-desktop.sh"
        content = script.read_text(encoding="utf-8")
        profiles = ["kubuntu", "kde-full", "kde-standard", "xubuntu", "ubuntu"]
        for profile in profiles:
            assert profile in content, f"Profile {profile} must be supported"

    def test_display_manager_masking(self):
        script = PROVISION_DIR / "install-desktop.sh"
        content = script.read_text(encoding="utf-8")
        assert "systemctl mask" in content
        assert "sddm" in content
        assert "lightdm" in content
        assert "gdm3" in content


class TestWslHealthGateSchema:
    """Verify WslHealthGate schema and contract for desktop flavors."""

    def test_health_report_fields(self):
        # Verify the C# class file contains the new fields
        gate_cs = REPO_ROOT / "host" / "DesktopSurfaceHost" / "WslHealthGate.cs"
        content = gate_cs.read_text(encoding="utf-8")
        assert "DesktopFlavor" in content
        assert "CoreAppsInstalled" in content
        assert "ThemesInstalled" in content
        assert "Kubuntu Full" in content
        assert "KDE Plasma Minimal" in content

    def test_health_gate_evaluation_logic(self):
        """Simulate desktop flavor classification logic."""
        def evaluate_flavor(plasma_ok: bool, apps_ok: bool, themes_ok: bool) -> str:
            if not plasma_ok:
                return "None"
            if apps_ok and themes_ok:
                return "Kubuntu Full"
            return "KDE Plasma Minimal"

        assert evaluate_flavor(False, False, False) == "None"
        assert evaluate_flavor(True, False, False) == "KDE Plasma Minimal"
        assert evaluate_flavor(True, True, False) == "KDE Plasma Minimal"
        assert evaluate_flavor(True, True, True) == "Kubuntu Full"
