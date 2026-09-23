#!/usr/bin/env python3
import glob
import os
import re
import subprocess
import sys

target_script = sys.argv[1] if len(sys.argv) > 1 else "/mnt/d/WinKDE/wsl/ensure-panel.js"
if not os.path.exists(target_script):
    print(f"Script not found: {target_script}", file=sys.stderr)
    sys.exit(1)

bus = ""
# 1. Try reading dbus.env created by start-panels.sh
env_file = os.path.expanduser("~/.local/state/nt-plasma/dbus.env")
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        for line in f:
            m = re.match(r"export DBUS_SESSION_BUS_ADDRESS=['\"]?([^'\"]+)['\"]?", line.strip())
            if m:
                candidate = m.group(1)
                sock = candidate.replace("unix:path=", "").split(",")[0]
                if os.path.exists(sock):
                    bus = candidate
                    break

# 2. Try plasmashell process environment
if not bus:
    for p in glob.glob("/proc/[0-9]*/cmdline"):
        try:
            with open(p, "rb") as f:
                cmd = f.read().decode("latin1")
            if "plasmashell" in cmd:
                pid = p.split("/")[2]
                with open(f"/proc/{pid}/environ", "rb") as f:
                    env = f.read().decode("latin1").split("\0")
                for e in env:
                    if e.startswith("DBUS_SESSION_BUS_ADDRESS="):
                        bus = e.split("=", 1)[1]
                        break
                if bus:
                    break
        except Exception:
            pass

if bus:
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = bus

with open(target_script, "r", encoding="utf-8") as f:
    js_code = f.read()

cmd = [
    "gdbus", "call",
    "--session",
    "--dest", "org.kde.plasmashell",
    "--object-path", "/PlasmaShell",
    "--method", "org.kde.PlasmaShell.evaluateScript",
    js_code
]

res = subprocess.run(cmd, capture_output=True, text=True)
if res.returncode != 0:
    print(f"Error evaluating script: {res.stderr.strip()}", file=sys.stderr)
    sys.exit(res.returncode)
else:
    print(res.stdout.strip())
