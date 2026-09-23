#!/usr/bin/env python3
"""
ntKDE Action Dispatcher
Dispatches user actions from KDE Plasma QML plasmoids to the running task bridge daemon
via a lightweight UNIX domain socket.
"""

import json
import os
import socket
import sys


def main() -> None:
    if len(sys.argv) < 2:
        print("ERR_NO_ACTION", flush=True)
        sys.exit(0)

    action = sys.argv[1]  # "activate", "minimize", "restore", "toggle", "close", "show_desktop", "minimize_all", "restore_all"
    hwnd = None
    if len(sys.argv) >= 3:
        try:
            # Strip any '#nonce' parameter added for cache busting
            raw = sys.argv[2].split("#")[0].strip()
            if raw and raw != "undefined" and raw != "0":
                hwnd = int(raw)
        except ValueError:
            hwnd = None

    sock_path = os.path.expanduser("~/.local/state/nt-plasma/bridge.sock")
    if not os.path.exists(sock_path):
        print("ERR_NO_SOCKET", flush=True)
        sys.exit(0)

    try:
        msg = {"action": action}
        if hwnd is not None:
            msg["hwnd"] = hwnd
        payload = json.dumps(msg) + "\n"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect(sock_path)
            s.sendall(payload.encode("utf-8"))
        print("OK", flush=True)
    except Exception as e:
        print(f"ERR_{e}", flush=True)


if __name__ == "__main__":
    main()
