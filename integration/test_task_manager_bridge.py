"""
Integration test suite for the ntKDE Native Task Manager Bridge (Zero-X11-Proxy).
Verifies tasks.json atomic serialization and UNIX socket action dispatching.
"""

import json
import os
import subprocess
import sys
import time
import unittest


class TaskManagerBridgeTests(unittest.TestCase):
    def test_tasks_json_pipeline_and_socket_action(self) -> None:
        """Verify that tasks are written to tasks.json and actions sent via bridge.sock are emitted."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        bridge_py = os.path.join(repo_root, "wsl", "kde-task-bridge.py")
        action_py = os.path.join(repo_root, "wsl", "send-action.py")

        # Start kde-task-bridge.py in WSL
        wsl_bridge_path = "/mnt/d/WinKDE/wsl/kde-task-bridge.py"
        wsl_action_path = "/mnt/d/WinKDE/wsl/send-action.py"

        proc = subprocess.Popen(
            ["wsl.exe", "-d", "Ubuntu", "-u", "jace479", "python3", wsl_bridge_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait for bridge to report ready on stderr
            ready_line = proc.stderr.readline()
            self.assertIn("started successfully", ready_line)

            # Send a sync command with 2 tasks
            sync_cmd = {
                "op": "sync",
                "tasks": [
                    {
                        "hwnd": 1001,
                        "title": "Google Chrome - Wikipedia",
                        "appId": "google-chrome",
                        "process": "chrome",
                        "active": True,
                        "minimized": False,
                    },
                    {
                        "hwnd": 1002,
                        "title": "Visual Studio Code",
                        "appId": "code",
                        "process": "code",
                        "active": False,
                        "minimized": True,
                    },
                ],
            }
            proc.stdin.write(json.dumps(sync_cmd) + "\n")
            proc.stdin.flush()
            time.sleep(0.5)

            # Verify tasks.json in WSL
            check_res = subprocess.run(
                [
                    "wsl.exe",
                    "-d",
                    "Ubuntu",
                    "-u",
                    "jace479",
                    "cat",
                    "/home/jace479/.local/state/nt-plasma/tasks.json",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(check_res.returncode, 0)
            data = json.loads(check_res.stdout)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["hwnd"], 1001)
            self.assertEqual(data[0]["icon"], "google-chrome")
            self.assertTrue(data[0]["active"])
            self.assertEqual(data[1]["hwnd"], 1002)
            self.assertEqual(data[1]["icon"], "visual-studio-code")
            self.assertTrue(data[1]["minimized"])

            # Send an action via send-action.py
            act_res = subprocess.run(
                [
                    "wsl.exe",
                    "-d",
                    "Ubuntu",
                    "-u",
                    "jace479",
                    "python3",
                    wsl_action_path,
                    "activate",
                    "1002",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(act_res.returncode, 0)

            # Read emitted action from stdout
            out_line = proc.stdout.readline().strip()
            emitted = json.loads(out_line)
            self.assertEqual(emitted["action"], "activate")
            self.assertEqual(emitted["hwnd"], 1002)

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

    def test_x11_ewmh_stub_and_event_dispatch(self) -> None:
        """Verify that X11 stub windows are registered in _NET_CLIENT_LIST and X11 click messages emit actions."""
        wsl_bridge_path = "/mnt/d/WinKDE/wsl/kde-task-bridge.py"

        proc = subprocess.Popen(
            ["wsl.exe", "-d", "Ubuntu", "-u", "jace479", "python3", wsl_bridge_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            ready_line = proc.stderr.readline()
            self.assertIn("started successfully", ready_line)

            # Add a Windows app
            add_cmd = {
                "op": "add",
                "hwnd": 9999,
                "title": "Test Spotify \u200b Window",
                "appId": "spotify",
                "process": "Spotify",
                "pid": 5555,
                "minimized": False,
                "active": False,
            }
            proc.stdin.write(json.dumps(add_cmd) + "\n")
            proc.stdin.flush()
            time.sleep(0.5)

            # Query X11 _NET_CLIENT_LIST
            xprop_res = subprocess.run(
                ["wsl.exe", "-d", "Ubuntu", "-u", "jace479", "xprop", "-root", "_NET_CLIENT_LIST"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(xprop_res.returncode, 0)
            self.assertIn("0x", xprop_res.stdout)
            xid_str = xprop_res.stdout.split()[-1]

            # Verify stub properties
            prop_res = subprocess.run(
                ["wsl.exe", "-d", "Ubuntu", "-u", "jace479", "xprop", "-id", xid_str, "_NET_WM_NAME", "WM_CLASS"],
                capture_output=True,
                text=True,
            )
            self.assertIn("Test Spotify", prop_res.stdout)
            self.assertIn("spotify", prop_res.stdout.lower())

            # Simulate KDE taskbar clicking the window (_NET_ACTIVE_WINDOW ClientMessage)
            send_click = (
                "import Xlib.display, Xlib.X, Xlib.protocol.event\n"
                "disp = Xlib.display.Display(':0')\n"
                f"xid = {xid_str}\n"
                "atom_active = disp.intern_atom('_NET_ACTIVE_WINDOW')\n"
                "event = Xlib.protocol.event.ClientMessage(window=disp.create_resource_object('window', xid), client_type=atom_active, data=(32, [1, 0, 0, 0, 0]))\n"
                "disp.screen().root.send_event(event, event_mask=Xlib.X.SubstructureNotifyMask)\n"
                "disp.sync()\n"
            )
            click_res = subprocess.run(
                ["wsl.exe", "-d", "Ubuntu", "-u", "jace479", "python3", "-c", send_click],
                capture_output=True,
                text=True,
            )
            self.assertEqual(click_res.returncode, 0)

            # Verify emitted action on bridge stdout
            out_line = proc.stdout.readline().strip()
            emitted = json.loads(out_line)
            self.assertEqual(emitted["action"], "toggle")
            self.assertEqual(emitted["hwnd"], 9999)

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    unittest.main(verbosity=2)
