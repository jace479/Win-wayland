#!/usr/bin/env python3
"""
ntKDE Winget Proxy Service
Bridges Windows winget.exe CLI to the KDE environment via a UNIX domain socket.
Parses winget's fixed-width text output into structured JSON for the QML app store.

Socket protocol: newline-delimited JSON request → newline-delimited JSON response.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Icon mapping: winget package ID prefix → Freedesktop icon name
# ---------------------------------------------------------------------------
ICON_MAP: Dict[str, str] = {
    # Browsers
    "mozilla.firefox": "firefox",
    "google.chrome": "google-chrome",
    "brave.brave": "brave-browser",
    "opera.opera": "opera",
    "vivaldi.vivaldi": "vivaldi",
    "microsoft.edge": "microsoft-edge",
    # Development
    "microsoft.visualstudiocode": "visual-studio-code",
    "jetbrains.intellijidea": "intellij-idea",
    "jetbrains.pycharm": "pycharm",
    "jetbrains.webstorm": "webstorm",
    "jetbrains.rider": "rider",
    "jetbrains.clion": "clion",
    "jetbrains.goland": "goland",
    "git.git": "git",
    "github.githubdesktop": "github",
    "python.python": "python",
    "nodejs.nodejs": "nodejs",
    "rustlang.rustup": "rust",
    "openjs.nodejs": "nodejs",
    # Media
    "spotify.spotify": "spotify",
    "videolan.vlc": "vlc",
    "audacity.audacity": "audacity",
    "obs-project.obsstudio": "obs",
    "gimp.gimp": "gimp",
    "inkscape.inkscape": "inkscape",
    "blender.blender": "blender",
    "handbrake.handbrake": "fr.handbrake.ghb",
    # Communication
    "discord.discord": "discord",
    "slacktechnologies.slack": "slack",
    "telegram.telegramdesktop": "telegram",
    "zoom.zoom": "zoom",
    "microsoft.teams": "teams",
    "signal.signal": "signal-desktop",
    # Utilities
    "notepad++.notepad++": "notepad",
    "7zip.7zip": "ark",
    "rarlab.winrar": "ark",
    "piriform.ccleaner": "sweeper",
    "voidtools.everything": "baloo",
    "flameshot.flameshot": "flameshot",
    "greenshot.greenshot": "applets-screenshooter",
    # Gaming
    "valve.steam": "steam",
    "epicgames.epicgameslauncher": "applications-games",
    "goggalaxy.goggalaxy": "applications-games",
    # Office
    "libreoffice.libreoffice": "libreoffice-startcenter",
    "thunderbird.thunderbird": "thunderbird",
    # System
    "microsoft.powershell": "utilities-terminal",
    "microsoft.windowsterminal": "utilities-terminal",
    "sysinternals.processhacker": "utilities-system-monitor",
}

# Broader fallback: match by keyword in package name/id
KEYWORD_ICON_MAP: Dict[str, str] = {
    "browser": "web-browser",
    "terminal": "utilities-terminal",
    "editor": "accessories-text-editor",
    "paint": "draw-brush",
    "calculator": "accessories-calculator",
    "music": "applications-multimedia",
    "video": "applications-multimedia",
    "game": "applications-games",
    "office": "applications-office",
    "mail": "internet-mail",
    "photo": "applications-graphics",
    "image": "applications-graphics",
    "chat": "internet-group-chat",
    "security": "security-high",
    "vpn": "network-vpn",
    "download": "folder-download",
    "torrent": "ktorrent",
    "archive": "ark",
    "backup": "drive-harddisk",
    "font": "preferences-desktop-font",
    "driver": "preferences-system-hardware",
}

# Desktop entry icon cache (same as kde-task-bridge.py)
_DESKTOP_ICON_CACHE: Dict[str, str] = {}
_CACHE_INITIALIZED: bool = False


def _init_desktop_cache() -> None:
    global _DESKTOP_ICON_CACHE, _CACHE_INITIALIZED
    if _CACHE_INITIALIZED:
        return
    _CACHE_INITIALIZED = True
    import glob
    app_dir = os.path.expanduser("~/.local/share/applications")
    if not os.path.exists(app_dir):
        return
    for path in glob.glob(os.path.join(app_dir, "nt-plasma-windows-*.desktop")):
        try:
            name, icon = "", ""
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("Name="):
                        name = line[5:].strip().lower()
                    elif line.startswith("Icon="):
                        icon = line[5:].strip()
            if name and icon and os.path.exists(icon):
                _DESKTOP_ICON_CACHE[name] = icon
        except Exception:
            continue


def resolve_icon(package_id: str, name: str = "") -> str:
    """Resolve a Freedesktop icon name for a winget package."""
    pid = package_id.lower().strip()
    pname = name.lower().strip()

    # 1. Exact match on package ID
    if pid in ICON_MAP:
        return ICON_MAP[pid]

    # 2. Prefix match (e.g. "JetBrains.IntelliJIDEA.Community" matches "jetbrains.intellijidea")
    for key, icon in ICON_MAP.items():
        if pid.startswith(key):
            return icon

    # 3. Check extracted Windows desktop shortcut icons
    _init_desktop_cache()
    for dname, icon_path in _DESKTOP_ICON_CACHE.items():
        if len(dname) >= 3 and (dname in pid or dname in pname):
            return icon_path

    # 4. Keyword match in name
    for keyword, icon in KEYWORD_ICON_MAP.items():
        if keyword in pname or keyword in pid:
            return icon

    return "package-x-generic"


# ---------------------------------------------------------------------------
# Winget CLI wrapper
# ---------------------------------------------------------------------------

import shutil

def _find_winget() -> str:
    exe = shutil.which("winget.exe") or shutil.which("winget")
    if exe:
        return exe
    candidates = [
        "/mnt/c/Users/jace0/AppData/Local/Microsoft/WindowsApps/winget.exe",
        "/mnt/c/Program Files/WindowsApps/Microsoft.DesktopAppInstaller_*/winget.exe",
    ]
    import glob
    for pat in candidates:
        matches = glob.glob(pat)
        if matches and os.path.exists(matches[0]):
            return matches[0]
    return "winget.exe"

WINGET_EXE = _find_winget()


def _run_winget(args: List[str], timeout: int = 60) -> Tuple[int, str, str]:
    """Run winget.exe from WSL and capture output."""
    cmd = [WINGET_EXE] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "WINGET_DISABLE_INTERACTIVITY": "1"},
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout exceeded"
    except FileNotFoundError:
        return -1, "", "winget.exe not found"
    except Exception as e:
        return -1, "", str(e)


def _run_winget_streaming(
    args: List[str],
    progress_callback: Optional[Callable[[str, int, str], None]] = None,
    timeout: int = 600,
) -> Tuple[int, str, str]:
    """
    Run winget.exe with real-time output parsing, emitting progress events:
    progress_callback(phase: "downloading" | "installing" | "done", progress: int (0..100), message: str)
    """
    cmd = [WINGET_EXE] + args
    env = {**os.environ, "WINGET_DISABLE_INTERACTIVITY": "1"}

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            errors="replace",
        )
    except FileNotFoundError:
        return -1, "", "winget.exe not found"
    except Exception as e:
        return -1, "", str(e)

    stdout_lines: List[str] = []
    current_phase = "downloading"
    current_progress = 10

    if progress_callback:
        progress_callback(current_phase, current_progress, "Starting Windows Package Manager...")

    ticker_stop = threading.Event()

    def _ticker():
        nonlocal current_progress
        while not ticker_stop.is_set():
            ticker_stop.wait(0.6)
            if ticker_stop.is_set():
                break
            if current_phase == "downloading" and current_progress < 85:
                current_progress = min(85, current_progress + 4)
                if progress_callback:
                    progress_callback(current_phase, current_progress, "Downloading package...")
            elif current_phase == "installing" and current_progress < 92:
                current_progress = min(92, current_progress + 3)
                if progress_callback:
                    progress_callback(current_phase, current_progress, "Installing package...")

    ticker_thread = threading.Thread(target=_ticker, daemon=True)
    ticker_thread.start()

    try:
        assert proc.stdout is not None
        for line in iter(proc.stdout.readline, ""):
            line_str = line.strip()
            stdout_lines.append(line)
            line_lower = line_str.lower()

            if "found" in line_lower and ("[" in line_str or "version" in line_lower):
                current_phase = "downloading"
                current_progress = max(current_progress, 15)
                if progress_callback:
                    progress_callback(current_phase, current_progress, line_str)
            elif "downloading" in line_lower:
                current_phase = "downloading"
                current_progress = max(current_progress, 30)
                if progress_callback:
                    progress_callback(current_phase, current_progress, "Downloading installer...")
            elif "verified installer hash" in line_lower or "hash" in line_lower:
                current_phase = "downloading"
                current_progress = 95
                if progress_callback:
                    progress_callback(current_phase, current_progress, "Verified installer hash")
            elif "starting package install" in line_lower or "installing" in line_lower:
                current_phase = "installing"
                current_progress = 20
                if progress_callback:
                    progress_callback(current_phase, current_progress, "Starting installation...")
            elif "starting package uninstall" in line_lower or "uninstalling" in line_lower:
                current_phase = "installing"
                current_progress = 30
                if progress_callback:
                    progress_callback(current_phase, current_progress, "Uninstalling application...")
            elif "successfully installed" in line_lower:
                current_phase = "installing"
                current_progress = 100
                if progress_callback:
                    progress_callback(current_phase, current_progress, "Successfully installed")
            elif "successfully uninstalled" in line_lower:
                current_phase = "installing"
                current_progress = 100
                if progress_callback:
                    progress_callback(current_phase, current_progress, "Successfully uninstalled")

        proc.stdout.close()
        proc.wait(timeout=15)
    except Exception as e:
        sys.stderr.write(f"[winget-proxy] Error streaming winget output: {e}\n")
    finally:
        ticker_stop.set()
        ticker_thread.join(timeout=1.0)

    full_output = "".join(stdout_lines)
    return proc.returncode, full_output, ""


def _parse_table(output: str) -> List[Dict[str, str]]:
    """
    Parse winget's fixed-width table output.
    Detects column boundaries from header line word positions.
    """
    lines = output.strip().split("\n")
    if len(lines) < 3:
        return []

    # Find separator line (contains mostly dashes)
    sep_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and all(c in "- " for c in stripped) and stripped.count("-") >= 5:
            sep_idx = i
            break

    if sep_idx < 1:
        return []

    header_line = lines[sep_idx - 1]

    # Find single-word header boundaries in header_line
    matches = list(re.finditer(r"\b[A-Za-z0-9_]+\b", header_line))
    if not matches:
        return []

    cols: List[Tuple[str, int, Optional[int]]] = []
    for i, m in enumerate(matches):
        col_name = m.group().lower()
        col_start = m.start()
        col_end = matches[i + 1].start() if i + 1 < len(matches) else None
        cols.append((col_name, col_start, col_end))

    results: List[Dict[str, str]] = []
    for line in lines[sep_idx + 1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("<") or "packages found" in stripped.lower() or "entries truncated" in stripped.lower():
            continue

        row: Dict[str, str] = {}
        for col_name, start, end in cols:
            if start < len(line):
                val = line[start:end].strip() if end is not None else line[start:].strip()
            else:
                val = ""
            row[col_name] = val

        if row.get("id") or row.get("name"):
            results.append(row)

    return results


def _parse_show(output: str) -> Dict[str, Any]:
    """Parse winget show output (key: value pairs, with multi-line values)."""
    info: Dict[str, Any] = {}
    lines = output.strip().split("\n")

    current_key = ""
    current_val = ""

    for line in lines:
        # Skip the "Found ..." header line
        if line.startswith("Found "):
            continue

        # Check if line is a key-value pair
        match = re.match(r"^([A-Za-z][A-Za-z\s]+?):\s*(.*)", line)
        if match:
            # Save previous key
            if current_key:
                info[current_key] = current_val.strip()
            current_key = match.group(1).strip().lower().replace(" ", "_")
            current_val = match.group(2)
        elif current_key and line.startswith("  "):
            # Continuation of multi-line value
            current_val += "\n" + line.strip()

    if current_key:
        info[current_key] = current_val.strip()

    return info


# ---------------------------------------------------------------------------
# High-level operations
# ---------------------------------------------------------------------------

def op_search(query: str, count: int = 25) -> Dict[str, Any]:
    """Search winget for packages matching query."""
    args = ["search", query, "--source", "winget", "--count", str(count),
            "--accept-source-agreements"]
    rc, stdout, stderr = _run_winget(args, timeout=30)
    if rc != 0 and not stdout.strip():
        return {"ok": False, "error": stderr or f"winget exit code {rc}", "results": []}

    rows = _parse_table(stdout)
    results = []
    for row in rows:
        pkg_id = row.get("id", "")
        pkg_name = row.get("name", "")
        results.append({
            "id": pkg_id,
            "name": pkg_name,
            "version": row.get("version", ""),
            "match": row.get("match", ""),
            "source": row.get("source", "winget"),
            "icon": resolve_icon(pkg_id, pkg_name),
        })
    return {"ok": True, "results": results}


def op_show(package_id: str) -> Dict[str, Any]:
    """Get detailed info about a specific package."""
    args = ["show", package_id, "--source", "winget", "--accept-source-agreements"]
    rc, stdout, stderr = _run_winget(args, timeout=30)
    if rc != 0 and not stdout.strip():
        return {"ok": False, "error": stderr or f"winget exit code {rc}"}

    info = _parse_show(stdout)
    info["icon"] = resolve_icon(package_id, info.get("name", ""))
    return {"ok": True, "package": info}


def op_list(query: Optional[str] = None) -> Dict[str, Any]:
    """List installed packages, optionally filtered by query."""
    args = ["list", "--accept-source-agreements"]
    if query:
        args.extend(["-q", query])
    rc, stdout, stderr = _run_winget(args, timeout=30)
    if rc != 0 and not stdout.strip():
        return {"ok": False, "error": stderr or f"winget exit code {rc}", "packages": []}

    rows = _parse_table(stdout)
    packages = []
    for row in rows:
        pkg_id = row.get("id", "")
        pkg_name = row.get("name", "")
        available = row.get("available", "")
        packages.append({
            "id": pkg_id,
            "name": pkg_name,
            "version": row.get("version", ""),
            "available": available,
            "source": row.get("source", ""),
            "upgradable": bool(available),
            "icon": resolve_icon(pkg_id, pkg_name),
        })
    return {"ok": True, "packages": packages}


def op_upgradable() -> Dict[str, Any]:
    """List packages with available upgrades."""
    args = ["upgrade", "--accept-source-agreements"]
    rc, stdout, stderr = _run_winget(args, timeout=30)

    rows = _parse_table(stdout)
    packages = []
    for row in rows:
        pkg_id = row.get("id", "")
        pkg_name = row.get("name", "")
        packages.append({
            "id": pkg_id,
            "name": pkg_name,
            "version": row.get("version", ""),
            "available": row.get("available", ""),
            "source": row.get("source", "winget"),
            "icon": resolve_icon(pkg_id, pkg_name),
        })
    return {"ok": True, "packages": packages}


def op_install(package_id: str, progress_cb: Optional[Callable[[str, int, str], None]] = None) -> Dict[str, Any]:
    """Install a winget package with real-time progress events."""
    args = [
        "install", package_id,
        "--source", "winget",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]
    rc, stdout, stderr = _run_winget_streaming(args, progress_callback=progress_cb, timeout=600)
    stdout_lower = stdout.lower()
    success = rc in (0, 3010, 1641) or "successfully installed" in stdout_lower or "already installed" in stdout_lower
    err = ""
    if not success:
        err = stderr.strip() if stderr else ""
        if not err:
            for l in reversed(stdout.splitlines()):
                ls = l.strip()
                if ls and not ls.startswith("-") and not ls.startswith("=") and len(ls) > 3:
                    err = ls
                    break
        if not err:
            err = f"Installation failed (exit code {rc})"

    if progress_cb:
        progress_cb("done" if success else "error", 100 if success else 0, "Complete" if success else err)
    return {
        "ok": success,
        "exit_code": rc,
        "output": stdout,
        "error": err if not success else "",
    }


def op_upgrade(package_id: str, progress_cb: Optional[Callable[[str, int, str], None]] = None) -> Dict[str, Any]:
    """Upgrade a winget package with real-time progress events."""
    args = [
        "upgrade", package_id,
        "--source", "winget",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]
    rc, stdout, stderr = _run_winget_streaming(args, progress_callback=progress_cb, timeout=600)
    stdout_lower = stdout.lower()
    success = rc in (0, 3010, 1641) or "successfully installed" in stdout_lower or "already installed" in stdout_lower or "no applicable update found" in stdout_lower
    err = ""
    if not success:
        err = stderr.strip() if stderr else ""
        if not err:
            for l in reversed(stdout.splitlines()):
                ls = l.strip()
                if ls and not ls.startswith("-") and not ls.startswith("=") and len(ls) > 3:
                    err = ls
                    break
        if not err:
            err = f"Upgrade failed (exit code {rc})"

    if progress_cb:
        progress_cb("done" if success else "error", 100 if success else 0, "Complete" if success else err)
    return {
        "ok": success,
        "exit_code": rc,
        "output": stdout,
        "error": err if not success else "",
    }


def op_uninstall(package_id: str, progress_cb: Optional[Callable[[str, int, str], None]] = None) -> Dict[str, Any]:
    """Uninstall a winget package with real-time progress events."""
    args = ["uninstall", package_id, "--accept-source-agreements"]
    rc, stdout, stderr = _run_winget_streaming(args, progress_callback=progress_cb, timeout=300)
    stdout_lower = stdout.lower()
    success = rc in (0, 3010, 1641) or "successfully uninstalled" in stdout_lower
    err = ""
    if not success:
        err = stderr.strip() if stderr else ""
        if not err:
            for l in reversed(stdout.splitlines()):
                ls = l.strip()
                if ls and not ls.startswith("-") and not ls.startswith("=") and len(ls) > 3:
                    err = ls
                    break
        if not err:
            err = f"Uninstall failed (exit code {rc})"

    if progress_cb:
        progress_cb("done" if success else "error", 100 if success else 0, "Complete" if success else err)
    return {
        "ok": success,
        "exit_code": rc,
        "output": stdout,
        "error": err if not success else "",
    }


# ---------------------------------------------------------------------------
# Socket server
# ---------------------------------------------------------------------------

OPERATIONS = {
    "ping": lambda req: {"ok": True, "pong": True},
    "search": lambda req: op_search(req.get("query", ""), req.get("count", 25)),
    "show": lambda req: op_show(req.get("id", "")),
    "list": lambda req: op_list(req.get("query")),
    "upgradable": lambda req: op_upgradable(),
    "install": lambda req: op_install(req.get("id", "")),
    "upgrade": lambda req: op_upgrade(req.get("id", "")),
    "uninstall": lambda req: op_uninstall(req.get("id", "")),
}


class WingetProxy:
    def __init__(self) -> None:
        self.state_dir = os.path.expanduser("~/.local/state/nt-plasma")
        os.makedirs(self.state_dir, exist_ok=True)
        self.sock_path = os.path.join(self.state_dir, "winget.sock")
        self.running = True

    def run(self) -> None:
        sys.stderr.write("[winget-proxy] ntKDE Winget Proxy starting...\n")
        sys.stderr.flush()

        if os.path.exists(self.sock_path):
            try:
                os.unlink(self.sock_path)
            except OSError:
                pass

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(self.sock_path)
        server.listen(8)
        server.settimeout(1.0)

        sys.stderr.write(f"[winget-proxy] Listening on {self.sock_path}\n")
        sys.stderr.flush()

        while self.running:
            try:
                conn, _ = server.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(conn,),
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    sys.stderr.write(f"[winget-proxy] Accept error: {e}\n")
                break

        server.close()
        try:
            os.unlink(self.sock_path)
        except OSError:
            pass

    def _handle_client(self, conn: socket.socket) -> None:
        with conn:
            try:
                # Read request (up to 8KB)
                data = b""
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in data:
                        break

                if not data:
                    return

                request_line = data.decode("utf-8").strip().split("\n")[0]
                req = json.loads(request_line)
                op_name = req.get("op", "")

                def progress_cb(phase: str, pct: int, msg: str) -> None:
                    evt = {
                        "type": "progress",
                        "phase": phase,
                        "progress": pct,
                        "message": msg,
                    }
                    try:
                        conn.sendall((json.dumps(evt) + "\n").encode("utf-8"))
                    except Exception:
                        pass

                sys.stderr.write(f"[winget-proxy] Handling op={op_name} req={req}\n")
                sys.stderr.flush()

                if op_name == "install":
                    result = op_install(req.get("id", ""), progress_cb=progress_cb)
                elif op_name == "upgrade":
                    result = op_upgrade(req.get("id", ""), progress_cb=progress_cb)
                elif op_name == "uninstall":
                    result = op_uninstall(req.get("id", ""), progress_cb=progress_cb)
                elif op_name in OPERATIONS:
                    result = OPERATIONS[op_name](req)
                else:
                    result = {"ok": False, "error": f"Unknown operation: {op_name}"}

                response = json.dumps(result) + "\n"
                conn.sendall(response.encode("utf-8"))

            except Exception as e:
                sys.stderr.write(f"[winget-proxy] Client error: {e}\n")
                sys.stderr.flush()
                try:
                    err = json.dumps({"ok": False, "error": str(e)}) + "\n"
                    conn.sendall(err.encode("utf-8"))
                except Exception:
                    pass


def main() -> None:
    proxy = WingetProxy()
    try:
        proxy.run()
    except KeyboardInterrupt:
        proxy.running = False


if __name__ == "__main__":
    main()
