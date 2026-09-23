import os, glob, subprocess, re

bus = None
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
    except Exception:
        pass

os.environ["DBUS_SESSION_BUS_ADDRESS"] = bus
cmd = [
    "gdbus", "call",
    "--session",
    "--dest", "org.kde.plasmashell",
    "--object-path", "/PlasmaShell",
    "--method", "org.kde.PlasmaShell.dumpCurrentLayoutJS"
]
res = subprocess.run(cmd, capture_output=True, text=True)
raw = res.stdout
bytes_vals = [int(b, 16) for b in re.findall(r'0x[0-9a-fA-F]+', raw)]
text = bytes(bytes_vals).decode("utf-8", errors="replace")
with open("/mnt/d/WinKDE/wsl/current_layout.js", "w", encoding="utf-8") as f:
    f.write(text)
print("Saved layout to current_layout.js, length:", len(text))
