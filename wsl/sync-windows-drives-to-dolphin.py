#!/usr/bin/env python3
"""Synchronize WSL-mounted Windows drives into Dolphin Places."""

from __future__ import annotations

import os
import string
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


XBEL = "http://www.freedesktop.org/standards/desktop-bookmarks"
ET.register_namespace("", XBEL)


def available_drives(mount_root: Path) -> list[tuple[str, Path]]:
    return [
        (letter, mount_root / letter.lower())
        for letter in string.ascii_uppercase
        if (mount_root / letter.lower()).is_dir()
    ]


def synchronize(places_path: Path, mount_root: Path) -> int:
    if places_path.exists():
        try:
            tree = ET.parse(places_path)
            root = tree.getroot()
        except ET.ParseError:
            root = ET.Element(f"{{{XBEL}}}xbel", {"version": "1.0"})
            tree = ET.ElementTree(root)
    else:
        root = ET.Element(f"{{{XBEL}}}xbel", {"version": "1.0"})
        tree = ET.ElementTree(root)

    for bookmark in list(root):
        if bookmark.tag != f"{{{XBEL}}}bookmark":
            continue
        if bookmark.get("ntkde-managed") == "windows-drive":
            root.remove(bookmark)

    for letter, path in available_drives(mount_root):
        bookmark = ET.SubElement(
            root,
            f"{{{XBEL}}}bookmark",
            {"href": path.resolve().as_uri(), "ntkde-managed": "windows-drive"},
        )
        ET.SubElement(bookmark, f"{{{XBEL}}}title").text = f"{letter}:"

    places_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(places_path, encoding="utf-8", xml_declaration=True)
    return len(available_drives(mount_root))


def main() -> int:
    places = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / ".local/share/user-places.xbel"
    mount_root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/mnt")
    print(f"windows_drives={synchronize(places, mount_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())