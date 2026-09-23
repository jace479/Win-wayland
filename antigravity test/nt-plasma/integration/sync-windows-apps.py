#!/usr/bin/env python3
import os
import sys
import glob
import re

START_DIRS = [
    "/mnt/c/ProgramData/Microsoft/Windows/Start Menu/Programs",
    "/mnt/c/Users/jace.zorn/AppData/Roaming/Microsoft/Windows/Start Menu/Programs"
]

OUT_DIR = os.path.expanduser("~/.local/share/applications/windows-apps")
os.makedirs(OUT_DIR, exist_ok=True)

BLACKLIST_TERMS = ["uninstall", "repair", "documentation", "readme", "help", "website", "remove"]

created = 0
for start_dir in START_DIRS:
    if not os.path.exists(start_dir):
        continue
    for root, dirs, files in os.walk(start_dir):
        for file in files:
            if file.lower().endswith(".lnk"):
                app_name = file[:-4].strip()
                if any(term in app_name.lower() for term in BLACKLIST_TERMS):
                    continue
                lnk_full_path = os.path.join(root, file)
                safe_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', app_name).strip('_')
                if not safe_name:
                    safe_name = "win_app"
                desktop_filename = f"win-{safe_name}.desktop"
                desktop_path = os.path.join(OUT_DIR, desktop_filename)

                content = f"""[Desktop Entry]
Type=Application
Name={app_name} (Windows)
Exec=/usr/local/bin/wsl-open "{lnk_full_path}"
Icon=application-x-ms-dos-executable
Categories=X-WindowsApps;Utility;
Terminal=false
Comment=Launch {app_name} on Windows
"""
                with open(desktop_path, "w", encoding="utf-8") as df:
                    df.write(content)
                created += 1

print(f"Successfully generated {created} Windows application desktop entries in {OUT_DIR}")
