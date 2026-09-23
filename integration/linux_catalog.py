"""Read visible Linux application desktop entries into the shared catalog."""

from __future__ import annotations

import configparser
import shutil
import shlex
from pathlib import Path

from .app_catalog import ApplicationEntry


def scan_linux_applications(roots: tuple[Path, ...]) -> tuple[ApplicationEntry, ...]:
    """Scan XDG application roots and return launchable application entries."""
    entries: list[ApplicationEntry] = []
    seen_ids: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.desktop")):
            entry = _read_desktop_entry(path)
            if entry is None or entry.application_id in seen_ids:
                continue
            entries.append(entry)
            seen_ids.add(entry.application_id)
    return tuple(entries)


def _read_desktop_entry(path: Path) -> ApplicationEntry | None:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        with path.open(encoding="utf-8") as desktop_file:
            parser.read_file(desktop_file)
        section = parser["Desktop Entry"]
    except (OSError, KeyError, configparser.Error):
        return None

    if section.get("Type") != "Application":
        return None
    if section.getboolean("Hidden", fallback=False) or section.getboolean(
        "NoDisplay", fallback=False
    ):
        return None
    try_exec = section.get("TryExec", "").strip()
    if try_exec:
        resolved_try_exec = (
            Path(try_exec).exists()
            if "/" in try_exec
            else shutil.which(try_exec) is not None
        )
        if not resolved_try_exec:
            return None

    name = section.get("Name", "").strip()
    command = section.get("Exec", "").strip()
    if not name or not command:
        return None
    try:
        command_parts = shlex.split(command)
    except ValueError:
        return None
    if not command_parts:
        return None
    command_parts = [part for part in command_parts if not part.startswith("%")]
    if any("%" in part for part in command_parts):
        return None

    categories = section.get("Categories", "").split(";")
    category = next((value for value in categories if value), "Other")
    return ApplicationEntry(
        application_id=f"linux:{path.stem}",
        display_name=name,
        executable=command_parts[0],
        arguments=tuple(command_parts[1:]),
        category=category,
        origin="linux",
        icon=section.get("Icon"),
    )