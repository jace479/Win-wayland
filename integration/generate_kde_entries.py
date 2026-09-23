"""Generate KDE application entries for host-owned Windows applications."""

from __future__ import annotations

import json
import re
import argparse
from pathlib import Path
from typing import Any


STANDARD_CATEGORIES = {
    "Audio": "AudioVideo",
    "AudioVideo": "AudioVideo",
    "Development": "Development",
    "Education": "Education",
    "Game": "Game",
    "Games": "Game",
    "Graphics": "Graphics",
    "Internet": "Network",
    "Network": "Network",
    "Office": "Office",
    "Settings": "Settings",
    "System": "System",
    "Utility": "Utility",
    "Utilities": "Utility",
}


def generate_entries(
    catalog_path: Path,
    output_directory: Path,
    launcher: str = "/opt/nt-plasma/bin/launch-windows-app",
) -> int:
    """Write one KDE entry per valid Windows catalog record."""
    catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    output_directory.mkdir(parents=True, exist_ok=True)
    written = 0
    for item in catalog:
        if not _valid_item(item):
            continue
        entry_id = _safe_id(item["id"])
        desktop = [
            "[Desktop Entry]",
            "Type=Application",
            f"Name={_desktop_value(item['name'])}",
            f"Exec={launcher} {item['id']}",
            f"Categories=X-Windows-Application;X-Windows-{_category(item.get('category', 'Other'))};",
            "NoDisplay=false",
            "Terminal=false",
            f"X-NT-Plasma-Source-Category={_desktop_value(item.get('category', 'Other'))}",
            f"X-NT-Plasma-Application-Id={_desktop_value(item['id'])}",
            "X-NT-Plasma-Origin=windows",
        ]
        icon = _linux_icon_path(item.get("icon"))
        if icon:
            desktop.insert(4, f"Icon={_desktop_value(icon)}")
        else:
            desktop.insert(4, "Icon=application-x-executable")
        (output_directory / f"nt-plasma-windows-{entry_id}.desktop").write_text(
            "\n".join(desktop) + "\n", encoding="utf-8"
        )
        written += 1
    return written


def _valid_item(item: Any) -> bool:
    return isinstance(item, dict) and bool(item.get("id")) and bool(item.get("name"))


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "-", value)


def _category(value: str) -> str:
    return STANDARD_CATEGORIES.get(value, "Utility")


def _desktop_value(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n")


def _linux_icon_path(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) > 2 and value[1] == ":":
        return f"/mnt/{value[0].lower()}{value[2:].replace(chr(92), '/') }"
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog_path", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("launcher", nargs="?", default="/opt/nt-plasma/bin/launch-windows-app")
    arguments = parser.parse_args()
    print(generate_entries(arguments.catalog_path, arguments.output_directory, arguments.launcher))