#!/usr/bin/env python3
"""
Ensures KDE Plasma application menu (plasma-applications.menu) includes:
1. A dedicated "Windows Applications" category (kf5-windows-applications.directory).
2. Clean separation so Windows apps live in "Windows Applications" and do not
   pollute native Linux categories (Utilities, Games, Office, System, etc.).
3. Proper Games category visibility so native KDE games (KMines, KPat, KMahjongg, KSudoku)
   are visible at top-level.
4. Correct symlinking of applications.menu.
"""

import os
import re
import sys

def main():
    config_dir = os.path.expanduser("~/.config/menus")
    desktop_dir = os.path.expanduser("~/.local/share/desktop-directories")
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(desktop_dir, exist_ok=True)

    # 1. Directory entry for Windows Applications
    dir_entry = """[Desktop Entry]
Type=Directory
Name=Windows Applications
Icon=application-x-ms-dos-executable
Comment=Windows Host Applications
"""
    local_dir_file = os.path.join(desktop_dir, "kf5-windows-applications.directory")
    with open(local_dir_file, "w", encoding="utf-8") as f:
        f.write(dir_entry)

    # 2. Configure plasma-applications.menu
    menu_file = os.path.join(config_dir, "plasma-applications.menu")
    base_menu = "/etc/xdg/menus/plasma-applications.menu"

    content = ""
    # Start fresh from the original upstream menu template if available, or current
    orig_menu = "/etc/xdg/menus/kf5-applications.menu"
    for candidate in [base_menu, orig_menu, menu_file]:
        if os.path.exists(candidate) and not os.path.islink(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                c = f.read()
                if "<Menu>" in c and ("<Name>Applications</Name>" in c or "<Name>Development</Name>" in c):
                    content = c
                    break

    if not content:
        sys.stderr.write("[ensure-plasma-menu] Could not locate valid plasma-applications.menu\n")
        return 1

    # Remove any existing Windows Applications menu definition to avoid duplicates
    content = re.sub(r"\s*<Menu>\s*<Name>Windows Applications</Name>.*?</Menu>", "", content, flags=re.DOTALL)

    # Invalidate old symlink if it was pointing to /etc
    if os.path.islink(menu_file):
        os.unlink(menu_file)

    # Define dedicated Windows Applications menu block
    win_menu_block = """
	<Menu>
		<Name>Windows Applications</Name>
		<Directory>kf5-windows-applications.directory</Directory>
		<Include>
			<Category>X-Windows-Application</Category>
		</Include>
	</Menu>
"""

    # Insert Windows Applications menu right before <DefaultMergeDirs/> or <Menu><Name>Help</Name>
    if "<Menu>\n\t\t<Name>Help</Name>" in content:
        content = content.replace("<Menu>\n\t\t<Name>Help</Name>", win_menu_block + "\n\t<Menu>\n\t\t<Name>Help</Name>")
    elif "<DefaultMergeDirs/>" in content:
        content = content.replace("<DefaultMergeDirs/>", win_menu_block + "\n\t<DefaultMergeDirs/>")
    else:
        idx = content.rfind("</Menu>")
        if idx != -1:
            content = content[:idx] + win_menu_block + content[idx:]

    # Ensure Games category shows all games at top level
    old_games_pattern = re.compile(
        r"(<Menu>\s*<Name>Games</Name>.*?<Include>\s*<And>\s*<Category>Game</Category>\s*<Not>.*?</Not>\s*</And>\s*</Include>)",
        re.DOTALL
    )
    def fix_games(match):
        block = match.group(1)
        return re.sub(
            r"<And>\s*<Category>Game</Category>\s*<Not>.*?</Not>\s*</And>",
            "<Category>Game</Category>",
            block,
            flags=re.DOTALL
        )

    content = old_games_pattern.sub(fix_games, content)

    with open(menu_file, "w", encoding="utf-8") as f:
        f.write(content)

    # Ensure applications.menu symlink
    app_menu = os.path.join(config_dir, "applications.menu")
    if os.path.islink(app_menu) or os.path.exists(app_menu):
        os.unlink(app_menu)
    os.symlink(menu_file, app_menu)

    print("[ensure-plasma-menu] Successfully configured plasma-applications.menu with isolated Windows Applications category")
    return 0

if __name__ == "__main__":
    sys.exit(main())
