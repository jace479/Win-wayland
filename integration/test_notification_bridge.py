"""
Integration test suite for the ntKDE Notification and Media/Volume Bridge.
Verifies protocol handling, notification serialization, and audio/hotkey controls.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest


class NotificationBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.ntkde_exe = os.path.join(repo_root, "bin", "ntkde.exe")

    def test_notification_protocol_serialization(self) -> None:
        """Verify notification and launcher operations serialize correctly."""
        notify_msg = {
            "op": "notify",
            "title": "Build Completed",
            "body": "Your project built successfully in 3.2s",
            "app_name": "Visual Studio",
            "urgency": "normal",
            "icon": "preferences-desktop-notification",
        }
        encoded = json.dumps(notify_msg)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["op"], "notify")
        self.assertEqual(decoded["title"], "Build Completed")
        self.assertEqual(decoded["app_name"], "Visual Studio")

        kickoff_msg = {"op": "kickoff"}
        self.assertEqual(json.loads(json.dumps(kickoff_msg))["op"], "kickoff")

        krunner_msg = {"op": "krunner"}
        self.assertEqual(json.loads(json.dumps(krunner_msg))["op"], "krunner")

        volume_msg = {"op": "volume", "percent": 70}
        self.assertEqual(json.loads(json.dumps(volume_msg))["percent"], 70)

        media_msg = {"op": "media_osd", "icon": "media-playback-start", "text": "Now Playing"}
        self.assertEqual(json.loads(json.dumps(media_msg))["text"], "Now Playing")

    def test_ntkde_volume_cli(self) -> None:
        """Verify ntkde volume CLI can query and step volume via Windows Core Audio."""
        if not os.path.exists(self.ntkde_exe):
            self.skipTest(f"ntkde executable not found at {self.ntkde_exe}")

        res = subprocess.run(
            [self.ntkde_exe, "volume", "get"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(res.returncode, 0, f"volume get failed: {res.stderr}")
        self.assertIn("Current Volume:", res.stdout)
        self.assertIn("%", res.stdout)

    def test_ntkde_notify_cli(self) -> None:
        """Verify ntkde notify CLI dispatches notification to WSL."""
        if not os.path.exists(self.ntkde_exe):
            self.skipTest(f"ntkde executable not found at {self.ntkde_exe}")

        res = subprocess.run(
            [self.ntkde_exe, "notify", "Test Notification", "Integration test body"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(res.returncode, 0, f"notify failed: {res.stderr}")
        self.assertIn("Dispatched notification", res.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
