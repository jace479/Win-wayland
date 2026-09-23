#!/usr/bin/env python3
"""
configure_default_panel.py
Configures KDE Plasma panels in ~/.config/plasma-org.kde.plasma.desktop-appletsrc
to use KDE's native org.kde.plasma.icontasks (Icons-Only Task Manager) by default,
which seamlessly displays Windows and Linux applications via EWMH metadata stubs.
"""

import os
import re
import sys


def configure_panel_config(config_path: str) -> bool:
    if not os.path.exists(config_path):
        return False

    with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    modified = False
    new_lines = []

    # Regex to find native icontasks/taskmanager and replace with org.ntkde.taskbar
    native_plugin_re = re.compile(r"^\s*plugin=org\.kde\.plasma\.(icontasks|taskmanager)\s*$")

    for line in lines:
        if native_plugin_re.match(line):
            new_lines.append("plugin=org.ntkde.taskbar\n")
            modified = True
        else:
            new_lines.append(line)

    if modified:
        tmp_path = config_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        os.replace(tmp_path, config_path)
        print(f"[configure_default_panel] Successfully updated {config_path} to use org.ntkde.taskbar.")
        return True
    else:
        content = "".join(lines)
        if "plugin=org.ntkde.taskbar" in content:
            print(f"[configure_default_panel] org.ntkde.taskbar is already configured in {config_path}.")
            return True
        else:
            print(f"[configure_default_panel] No taskbar found to update in {config_path}.")
            return False


def main() -> None:
    targets = [
        os.path.expanduser("~/.config/plasma-org.kde.plasma.desktop-appletsrc"),
        "/home/jace479/.config/plasma-org.kde.plasma.desktop-appletsrc",
    ]
    seen = set()
    for t in targets:
        if t not in seen and os.path.exists(t):
            seen.add(t)
            configure_panel_config(t)


if __name__ == "__main__":
    main()
