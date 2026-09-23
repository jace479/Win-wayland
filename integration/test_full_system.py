#!/usr/bin/env python3
"""
WinKDE Full System Test Suite
Verifies all subsystems of WinKDE end-to-end:
1. WSL & WSLg Environment
2. Application Catalog & Windows Desktop Redirection
3. Zero-TCP IPC Compliance
4. Desktop Surface Host (.NET)
5. KDE Plasma Panels & Applets
6. Bidirectional Taskbar Window Proxy Bridge
"""

import json
import os
import subprocess
import sys
import time
import unittest


class TestWslEnvironment(unittest.TestCase):
    """Verifies WSL distro, user, and WSLg graphics/audio environment."""

    def test_01_wsl_distro_and_user(self):
        res = subprocess.run(
            ["wsl.exe", "-d", "Ubuntu", "-u", "jace479", "-e", "id", "-u"],
            capture_output=True, text=True, check=True
        )
        self.assertEqual(res.stdout.strip(), "1000", "User UID must be 1000")

    def test_02_wslg_x11_display(self):
        res = subprocess.run(
            ["wsl.exe", "-d", "Ubuntu", "-u", "jace479", "-e", "bash", "-c", "DISPLAY=:0 xprop -root -len 1"],
            capture_output=True, text=True
        )
        self.assertEqual(res.returncode, 0, "WSLg X11 display :0 must be accessible")

    def test_03_kde_plasmashell_installed(self):
        res = subprocess.run(
            ["wsl.exe", "-d", "Ubuntu", "-u", "jace479", "-e", "plasmashell", "--version"],
            capture_output=True, text=True
        )
        self.assertEqual(res.returncode, 0, "plasmashell must be installed")
        self.assertIn("plasmashell", res.stdout.lower())


class TestAppCatalogAndDesktop(unittest.TestCase):
    """Verifies Windows app synchronization and desktop folder redirection."""

    def test_01_desktop_symlink(self):
        res = subprocess.run(
            ["wsl.exe", "-d", "Ubuntu", "-u", "jace479", "-e", "readlink", "-f", "/home/jace479/Desktop"],
            capture_output=True, text=True, check=True
        )
        target = res.stdout.strip()
        self.assertTrue(
            target.startswith("/mnt/c/Users/"),
            f"~/Desktop should link to Windows Desktop folder, got: {target}"
        )
        self.assertTrue(
            "Desktop" in target,
            f"Target path must end with Desktop, got: {target}"
        )

    def test_02_synced_desktop_entries(self):
        res = subprocess.run(
            ["wsl.exe", "-d", "Ubuntu", "-u", "jace479", "-e", "bash", "-c", "ls -1 ~/.local/share/applications/nt-plasma-windows-*.desktop 2>/dev/null | wc -l"],
            capture_output=True, text=True, check=True
        )
        count = int(res.stdout.strip() or "0")
        self.assertGreater(count, 30, f"Expected >30 synced Windows desktop entries, found {count}")


class TestZeroTcpCompliance(unittest.TestCase):
    """Verifies that WinKDE uses zero TCP/IP sockets for IPC."""

    def test_01_no_ntkde_listening_ports(self):
        res = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, check=True
        )
        # Find PIDs of ntkde processes
        ps_res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-Process ntkde -ErrorAction SilentlyContinue).Id"],
            capture_output=True, text=True
        )
        ntkde_pids = [p.strip() for p in ps_res.stdout.splitlines() if p.strip()]
        for line in res.stdout.splitlines():
            if "LISTENING" in line:
                for pid in ntkde_pids:
                    self.assertFalse(
                        line.endswith(pid),
                        f"ntkde (PID {pid}) must NOT listen on TCP ports! Found: {line}"
                    )


class TestKdePanelsAndLayout(unittest.TestCase):
    """Verifies that KDE panels are configured with kickoff and org.ntkde.taskbar."""

    def test_01_panel_layout_has_taskbar(self):
        # Verify ensure-panel.js configures kickoff and org.ntkde.taskbar
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ensure_panel_path = os.path.join(repo_root, "wsl", "ensure-panel.js")
        with open(ensure_panel_path, "r", encoding="utf-8") as f:
            js_code = f.read()
        self.assertIn("org.ntkde.taskbar", js_code, "ensure-panel.js must configure org.ntkde.taskbar")
        self.assertIn("org.kde.plasma.kickoff", js_code, "ensure-panel.js must configure kickoff launcher")


class TestTaskbarWindowBridge(unittest.TestCase):
    """Verifies the Zero-Proxy Native Windows-to-KDE taskbar bridge."""

    def test_01_plasmoid_metadata_valid(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        meta_path = os.path.join(repo_root, "wsl", "plasmoids", "org.ntkde.taskbar", "metadata.json")
        self.assertTrue(os.path.exists(meta_path), "org.ntkde.taskbar metadata.json must exist")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(meta["KPlugin"]["Id"], "org.ntkde.taskbar")

    def test_02_tasks_json_available(self):
        res = subprocess.run(
            ["wsl.exe", "-d", "Ubuntu", "-u", "jace479", "-e", "bash", "-c", "cat ~/.local/state/nt-plasma/tasks.json"],
            capture_output=True, text=True
        )
        self.assertEqual(res.returncode, 0, "tasks.json should be readable in WSL")
        data = json.loads(res.stdout)
        self.assertIsInstance(data, list, "tasks.json must contain a JSON array of tasks")

    def test_03_zero_proxy_windows_prevent_weston_crash(self):
        # Verify that we do NOT pollute _NET_CLIENT_LIST with offscreen proxy windows
        res = subprocess.run(
            ["wsl.exe", "-d", "Ubuntu", "-u", "jace479", "-e", "bash", "-c", "DISPLAY=:0 xprop -root _NET_CLIENT_LIST || true"],
            capture_output=True, text=True
        )
        # In zero-proxy mode, we should not have dummy windows at -5000,-5000
        output = res.stdout.strip()
        if "_NET_CLIENT_LIST(WINDOW)" in output and "#" in output:
            ids = output.split("#")[1].replace(",", "").split()
            # If any window exists, it should not be a dummy proxy
            for wid in ids[:3]:
                prop_res = subprocess.run(
                    ["wsl.exe", "-d", "Ubuntu", "-u", "jace479", "-e", "bash", "-c", f"DISPLAY=:0 xprop -id {wid} WM_NAME || true"],
                    capture_output=True, text=True
                )
                self.assertNotIn("ntKDE Proxy", prop_res.stdout, "No dummy ntKDE proxy windows should exist on X11 root")


if __name__ == "__main__":
    unittest.main(verbosity=2)
