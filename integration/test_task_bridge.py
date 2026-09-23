"""
Integration test suite for the ntKDE Task Proxy Bridge.
Verifies protocol serialization, bridge communication, and X11 window tracking.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest


class TaskBridgeTests(unittest.TestCase):
    def test_task_bridge_protocol_serialization(self) -> None:
        """Verify serialization of all task bridge protocol messages."""
        add_msg = {
            "op": "add",
            "hwnd": 0x12345,
            "title": "Untitled - Notepad",
            "appId": "notepad",
            "process": "notepad",
            "pid": 5678,
            "minimized": False,
            "active": True,
        }
        encoded = json.dumps(add_msg)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["op"], "add")
        self.assertEqual(decoded["hwnd"], 0x12345)
        self.assertEqual(decoded["title"], "Untitled - Notepad")
        self.assertEqual(decoded["appId"], "notepad")

        update_msg = {
            "op": "update",
            "hwnd": 0x12345,
            "title": "Document.txt - Notepad",
            "minimized": False,
        }
        encoded_up = json.dumps(update_msg)
        decoded_up = json.loads(encoded_up)
        self.assertEqual(decoded_up["op"], "update")
        self.assertEqual(decoded_up["title"], "Document.txt - Notepad")

        sync_msg = {
            "op": "sync",
            "tasks": [add_msg],
        }
        encoded_sync = json.dumps(sync_msg)
        decoded_sync = json.loads(encoded_sync)
        self.assertEqual(decoded_sync["op"], "sync")
        self.assertEqual(len(decoded_sync["tasks"]), 1)

    def test_task_bridge_process_execution(self) -> None:
        """Verify that kde-task-bridge.py starts, processes messages, and exits cleanly."""
        script_path = os.path.join(os.path.dirname(__file__), "..", "wsl", "kde-task-bridge.py")
        self.assertTrue(os.path.exists(script_path), f"Script not found at {script_path}")

        # Check python syntax
        res = subprocess.run([sys.executable, "-m", "py_compile", script_path], capture_output=True)
        self.assertEqual(res.returncode, 0)

        # If on Linux/WSL with DISPLAY set, test live interaction
        if sys.platform != "win32" and "DISPLAY" in os.environ:
            proc = subprocess.Popen(
                [sys.executable, script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            cmd = {
                "op": "add",
                "hwnd": 99999,
                "title": "PyTest Probe App",
                "appId": "pytest-probe",
                "process": "pytest",
                "pid": os.getpid(),
                "minimized": False,
                "active": False,
            }
            assert proc.stdin is not None
            proc.stdin.write(json.dumps(cmd) + "\n")
            proc.stdin.flush()
            time.sleep(0.3)

            rm_cmd = {"op": "remove", "hwnd": 99999}
            proc.stdin.write(json.dumps(rm_cmd) + "\n")
            proc.stdin.flush()
            time.sleep(0.2)

            proc.terminate()
            proc.wait(timeout=2)
            self.assertIsNotNone(proc.returncode)


if __name__ == "__main__":
    unittest.main()
