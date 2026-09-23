#!/usr/bin/env python3
"""
ntKDE Task Proxy Bridge (Zero-TCP & Zero-Proxy-Window)
Bridges native Windows application windows to the native KDE Plasma Task Manager plasmoid (org.ntkde.taskbar).
Publishes state atomically via ~/.local/state/nt-plasma/tasks.json and accepts user actions via a UNIX domain socket.
Dispatches DBus notifications, Kickoff, KRunner, and volume OSD overlays.
"""

from __future__ import annotations

import glob
import json
import os
import socket
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional

ICON_MAP: Dict[str, str] = {
    "chrome": "google-chrome",
    "google-chrome": "google-chrome",
    "msedge": "msedge",
    "firefox": "firefox",
    "code": "visual-studio-code",
    "devenv": "visual-studio",
    "antigravity": "visual-studio-code",
    "antigravity ide": "visual-studio-code",
    "explorer": "system-file-manager",
    "files": "system-file-manager",
    "windowsterminal": "utilities-terminal",
    "powershell": "utilities-terminal",
    "cmd": "utilities-terminal",
    "notepad": "accessories-text-editor",
    "notepad++": "accessories-text-editor",
    "slack": "slack",
    "discord": "discord",
    "spotify": "spotify",
    "telegram": "telegram",
    "steam": "steam",
    "taskmgr": "utilities-system-monitor",
    "taskmanager": "utilities-system-monitor",
    "calculator": "accessories-calculator",
    "calc": "accessories-calculator",
    "calculatorapp": "accessories-calculator",
    "snippingtool": "applets-screenshooter",
    "mspaint": "draw-brush",
    "paint": "draw-brush",
    "systemsettings": "preferences-system",
    "settings": "preferences-system",
    "calendar": "view-calendar",
    "phoneexperiencehost": "phone",
    "phonelink": "phone",
    "word": "x-office-document",
    "excel": "x-office-spreadsheet",
    "powerpnt": "x-office-presentation",
    "onenote": "accessories-text-editor",
    "teams": "teams",
    "whatsapp": "whatsapp",
}

_DESKTOP_ICON_CACHE: Dict[str, str] = {}
_CACHE_INITIALIZED: bool = False


def _init_desktop_cache() -> None:
    global _DESKTOP_ICON_CACHE, _CACHE_INITIALIZED
    if _CACHE_INITIALIZED:
        return
    _CACHE_INITIALIZED = True
    app_dir = os.path.expanduser("~/.local/share/applications")
    if not os.path.exists(app_dir):
        return
    for path in glob.glob(os.path.join(app_dir, "nt-plasma-windows-*.desktop")):
        try:
            name, icon, aid = "", "", ""
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("Name="):
                        name = line[5:].strip().lower()
                    elif line.startswith("Icon="):
                        icon = line[5:].strip()
                    elif line.startswith("X-NT-Plasma-Application-Id="):
                        aid = line[27:].strip().lower()
            if icon and os.path.exists(icon):
                if name:
                    _DESKTOP_ICON_CACHE[name] = icon
                if aid:
                    _DESKTOP_ICON_CACHE[aid] = icon
        except Exception:
            continue


def resolve_icon(app_id: str, process: str, title: str = "") -> str:
    proc_clean = process.lower().replace(".exe", "").strip()
    app_clean = app_id.lower().strip()
    title_clean = title.lower().strip()

    # 1. Match well-known Freedesktop icon names
    if proc_clean in ICON_MAP:
        return ICON_MAP[proc_clean]
    if app_clean in ICON_MAP:
        return ICON_MAP[app_clean]

    # 2. Match extracted Windows desktop shortcut icons (crisp native PNGs on disk)
    _init_desktop_cache()
    for key in (app_clean, proc_clean):
        if key and key in _DESKTOP_ICON_CACHE:
            return _DESKTOP_ICON_CACHE[key]

    for name, icon_path in _DESKTOP_ICON_CACHE.items():
        if len(name) >= 4 and ((name in app_clean) or (name in proc_clean) or (name in title_clean)):
            return icon_path

    for key, icon in ICON_MAP.items():
        if key in proc_clean or key in app_clean or key in title_clean:
            return icon

    return "preferences-system-windows"



try:
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False


class KWinDbusService(dbus.service.Object if HAS_DBUS else object):
    def __init__(self, bus: Any, bridge: "TaskBridge") -> None:
        self.bridge = bridge
        self._showing_desktop = False
        if HAS_DBUS:
            bus_name = dbus.service.BusName("org.kde.KWin", bus=bus)
            super().__init__(bus_name, "/KWin")

    def set_showing_desktop(self, showing: bool) -> None:
        if self._showing_desktop != showing:
            self._showing_desktop = showing
            if HAS_DBUS:
                try:
                    self.showingDesktopChanged(showing)
                except Exception:
                    pass

    if HAS_DBUS:
        @dbus.service.method("org.kde.KWin", in_signature="b", out_signature="")
        def showDesktop(self, showing: bool) -> None:
            self._showing_desktop = bool(showing)
            try:
                self.showingDesktopChanged(self._showing_desktop)
            except Exception:
                pass
            self.bridge._emit("show_desktop" if self._showing_desktop else "restore_all")

        @dbus.service.method("org.kde.KWin", in_signature="", out_signature="")
        def toggleDesktop(self) -> None:
            self._showing_desktop = not self._showing_desktop
            try:
                self.showingDesktopChanged(self._showing_desktop)
            except Exception:
                pass
            self.bridge._emit("show_desktop" if self._showing_desktop else "restore_all")

        @dbus.service.signal("org.kde.KWin", signature="b")
        def showingDesktopChanged(self, showing: bool) -> None:
            pass

        @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="ss", out_signature="v")
        def Get(self, iface: str, prop: str) -> Any:
            if prop == "showingDesktop":
                return dbus.Boolean(self._showing_desktop)
            raise dbus.exceptions.DBusException("Unknown property")

        @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="s", out_signature="a{sv}")
        def GetAll(self, iface: str) -> Dict[str, Any]:
            if iface == "org.kde.KWin":
                return {"showingDesktop": dbus.Boolean(self._showing_desktop)}
            return {}


try:
    import Xlib.display
    import Xlib.X
    import Xlib.Xatom
    import Xlib.protocol.event
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False


class X11StubManager:
    def __init__(self, bridge: "TaskBridge", display_str: str = ":0") -> None:
        self.bridge = bridge
        self.display_str = display_str
        self.disp: Optional[Any] = None
        self.root: Optional[Any] = None
        self.hwnd_to_xid: Dict[int, int] = {}
        self.xid_to_hwnd: Dict[int, int] = {}
        self.windows: Dict[int, Any] = {}
        self.lock = threading.RLock()
        self.running = True

        # Atoms
        self.atom_client_list = None
        self.atom_client_list_stacking = None
        self.atom_active_window = None
        self.atom_close_window = None
        self.atom_net_wm_name = None
        self.atom_utf8_string = None
        self.atom_window_type = None
        self.atom_window_type_normal = None
        self.atom_wm_state = None
        self.atom_net_wm_state = None
        self.atom_net_wm_state_hidden = None
        self.atom_net_wm_pid = None
        self.atom_wm_protocols = None
        self.atom_wm_delete_window = None
        self.atom_supported = None

    def start(self) -> bool:
        if not HAS_XLIB:
            sys.stderr.write("[task-bridge] python-xlib not available, skipping X11 stubs.\n")
            return False

        try:
            disp_target = os.environ.get("DISPLAY", self.display_str)
            self.disp = Xlib.display.Display(disp_target)
            self.root = self.disp.screen().root

            # Intern atoms
            self.atom_client_list = self.disp.intern_atom("_NET_CLIENT_LIST")
            self.atom_client_list_stacking = self.disp.intern_atom("_NET_CLIENT_LIST_STACKING")
            self.atom_active_window = self.disp.intern_atom("_NET_ACTIVE_WINDOW")
            self.atom_close_window = self.disp.intern_atom("_NET_CLOSE_WINDOW")
            self.atom_net_wm_name = self.disp.intern_atom("_NET_WM_NAME")
            self.atom_utf8_string = self.disp.intern_atom("UTF8_STRING")
            self.atom_window_type = self.disp.intern_atom("_NET_WM_WINDOW_TYPE")
            self.atom_window_type_normal = self.disp.intern_atom("_NET_WM_WINDOW_TYPE_NORMAL")
            self.atom_wm_state = self.disp.intern_atom("WM_STATE")
            self.atom_net_wm_state = self.disp.intern_atom("_NET_WM_STATE")
            self.atom_net_wm_state_hidden = self.disp.intern_atom("_NET_WM_STATE_HIDDEN")
            self.atom_net_wm_pid = self.disp.intern_atom("_NET_WM_PID")
            self.atom_wm_protocols = self.disp.intern_atom("WM_PROTOCOLS")
            self.atom_wm_delete_window = self.disp.intern_atom("WM_DELETE_WINDOW")
            self.atom_supported = self.disp.intern_atom("_NET_SUPPORTED")

            # Update _NET_SUPPORTED on root window
            self._update_net_supported()
            self._sync_client_list()

            # Listen for client messages on the root window
            try:
                self.root.change_attributes(event_mask=Xlib.X.PropertyChangeMask | Xlib.X.SubstructureNotifyMask)
            except Exception:
                pass

            self.disp.sync()

            # Start event loop thread
            t = threading.Thread(target=self._event_loop, daemon=True)
            t.start()
            return True
        except Exception as e:
            sys.stderr.write(f"[task-bridge] Failed to initialize X11 Stub Manager: {e}\n")
            return False

    def _update_net_supported(self) -> None:
        try:
            prop = self.root.get_full_property(self.atom_supported, Xlib.Xatom.ATOM)
            supported = prop.value.tolist() if prop and prop.value is not None else []
            needed = [
                self.atom_client_list,
                self.atom_client_list_stacking,
                self.atom_active_window,
                self.atom_close_window,
                self.atom_net_wm_name,
                self.atom_window_type,
                self.atom_net_wm_state,
                self.atom_net_wm_state_hidden,
            ]
            changed = False
            for atom in needed:
                if atom not in supported:
                    supported.append(atom)
                    changed = True
            if changed:
                self.root.change_property(self.atom_supported, Xlib.Xatom.ATOM, 32, supported)
        except Exception as e:
            sys.stderr.write(f"[task-bridge] Failed to update _NET_SUPPORTED: {e}\n")

    def _sync_client_list(self) -> None:
        if not self.disp or not self.root:
            return
        with self.lock:
            xids = list(self.xid_to_hwnd.keys())
        try:
            self.root.change_property(self.atom_client_list, Xlib.Xatom.WINDOW, 32, xids)
            self.root.change_property(self.atom_client_list_stacking, Xlib.Xatom.WINDOW, 32, xids)
            self.disp.sync()
        except Exception as e:
            sys.stderr.write(f"[task-bridge] Failed to sync _NET_CLIENT_LIST: {e}\n")

    def add_window(self, hwnd: int, title: str, app_id: str, process: str, pid: int, minimized: bool = False, active: bool = False) -> None:
        if not self.disp or not self.root:
            return

        with self.lock:
            already_exists = hwnd in self.hwnd_to_xid

        if already_exists:
            self.update_window(hwnd, title, minimized, active)
            return

        with self.lock:
            try:
                # Create a completely headless, invisible InputOnly window placed well offscreen.
                # InputOnly windows have no visual buffers, no color depth, and CANNOT be rendered or framed by Weston/MSRDC.
                win = self.root.create_window(
                    -1000, -1000, 1, 1, 0,
                    0,
                    Xlib.X.InputOnly,
                    Xlib.X.CopyFromParent,
                    override_redirect=1,
                    event_mask=Xlib.X.PropertyChangeMask | Xlib.X.StructureNotifyMask
                )

                # WM_CLASS (res_name, res_class) - safely ASCII-encoded for ICCCM
                try:
                    res_name = process.lower().replace(".exe", "").encode("ascii", errors="replace").decode("ascii")
                    res_class = (app_id if app_id else res_name.capitalize()).encode("ascii", errors="replace").decode("ascii")
                    win.set_wm_class(res_name, res_class)
                except Exception:
                    pass

                # Titles: UTF-8 for _NET_WM_NAME (modern EWMH), sanitized Latin-1 fallback for WM_NAME (ICCCM)
                try:
                    win.change_property(self.atom_net_wm_name, self.atom_utf8_string, 8, title.encode("utf-8", errors="replace"))
                except Exception:
                    pass

                try:
                    safe_title = title.encode("latin-1", errors="replace").decode("latin-1")
                    win.set_wm_name(safe_title)
                except Exception:
                    pass

                # Window type: NORMAL
                try:
                    win.change_property(self.atom_window_type, Xlib.Xatom.ATOM, 32, [self.atom_window_type_normal])
                except Exception:
                    pass

                # PID
                try:
                    win.change_property(self.atom_net_wm_pid, Xlib.Xatom.CARDINAL, 32, [pid])
                except Exception:
                    pass

                # Protocols: WM_DELETE_WINDOW
                try:
                    win.change_property(self.atom_wm_protocols, Xlib.Xatom.ATOM, 32, [self.atom_wm_delete_window])
                except Exception:
                    pass

                # State
                try:
                    state_val = 3 if minimized else 1
                    win.change_property(self.atom_wm_state, self.atom_wm_state, 32, [state_val, 0])
                    if minimized:
                        win.change_property(self.atom_net_wm_state, Xlib.Xatom.ATOM, 32, [self.atom_net_wm_state_hidden])
                    else:
                        win.change_property(self.atom_net_wm_state, Xlib.Xatom.ATOM, 32, [])
                except Exception:
                    pass

                # Map window so XWindowTasksModel recognizes it
                try:
                    win.map()
                except Exception:
                    pass

                self.hwnd_to_xid[hwnd] = win.id
                self.xid_to_hwnd[win.id] = hwnd
                self.windows[hwnd] = win

                if active:
                    try:
                        self.root.change_property(self.atom_active_window, Xlib.Xatom.WINDOW, 32, [win.id])
                    except Exception:
                        pass

                self.disp.sync()
            except Exception as e:
                sys.stderr.write(f"[task-bridge] Failed to create X11 stub window for HWND {hwnd}: {e}\n")
                return

        self._sync_client_list()

    def update_window(self, hwnd: int, title: Optional[str] = None, minimized: Optional[bool] = None, active: Optional[bool] = None) -> None:
        if not self.disp or not self.root:
            return

        with self.lock:
            win = self.windows.get(hwnd)
            if not win:
                return

            try:
                if title is not None:
                    try:
                        win.change_property(self.atom_net_wm_name, self.atom_utf8_string, 8, title.encode("utf-8", errors="replace"))
                    except Exception:
                        pass
                    try:
                        safe_title = title.encode("latin-1", errors="replace").decode("latin-1")
                        win.set_wm_name(safe_title)
                    except Exception:
                        pass

                if minimized is not None:
                    try:
                        state_val = 3 if minimized else 1
                        win.change_property(self.atom_wm_state, self.atom_wm_state, 32, [state_val, 0])
                        if minimized:
                            win.change_property(self.atom_net_wm_state, Xlib.Xatom.ATOM, 32, [self.atom_net_wm_state_hidden])
                        else:
                            win.change_property(self.atom_net_wm_state, Xlib.Xatom.ATOM, 32, [])
                    except Exception:
                        pass

                if active is True:
                    try:
                        self.root.change_property(self.atom_active_window, Xlib.Xatom.WINDOW, 32, [win.id])
                    except Exception:
                        pass

                self.disp.sync()
            except Exception as e:
                sys.stderr.write(f"[task-bridge] Failed to update X11 stub window for HWND {hwnd}: {e}\n")

    def set_active_window(self, hwnd: int) -> None:
        if not self.disp or not self.root:
            return
        with self.lock:
            xid = self.hwnd_to_xid.get(hwnd)
            if not xid:
                return
            try:
                self.root.change_property(self.atom_active_window, Xlib.Xatom.WINDOW, 32, [xid])
                self.disp.sync()
            except Exception:
                pass

    def remove_window(self, hwnd: int) -> None:
        if not self.disp:
            return

        with self.lock:
            xid = self.hwnd_to_xid.pop(hwnd, None)
            if xid:
                self.xid_to_hwnd.pop(xid, None)
            win = self.windows.pop(hwnd, None)
            if win:
                try:
                    win.unmap()
                    win.destroy()
                    self.disp.sync()
                except Exception:
                    pass

        self._sync_client_list()

    def sync_all(self, tasks_dict: Dict[int, Dict[str, Any]]) -> None:
        current_hwnds = set(tasks_dict.keys())
        with self.lock:
            existing_hwnds = set(self.hwnd_to_xid.keys())

        for dead_hwnd in (existing_hwnds - current_hwnds):
            self.remove_window(dead_hwnd)

        for hwnd, t in tasks_dict.items():
            self.add_window(
                hwnd=hwnd,
                title=t.get("title", "Windows Application"),
                app_id=t.get("app_id", "windows-app"),
                process=t.get("process", "app"),
                pid=t.get("pid", 1000),
                minimized=t.get("minimized", False),
                active=t.get("active", False)
            )

    def _event_loop(self) -> None:
        while self.running and self.disp:
            try:
                event = self.disp.next_event()
                if not event:
                    continue

                if event.type == Xlib.X.ClientMessage:
                    msg_type = getattr(event, "client_type", getattr(event, "message_type", None))
                    target_xid = event.window.id if hasattr(event.window, "id") else int(event.window)

                    if msg_type == self.atom_active_window:
                        hwnd = self.xid_to_hwnd.get(target_xid)
                        if not hwnd and hasattr(event, "data") and len(event.data.data32) > 0:
                            alt_xid = event.data.data32[0]
                            hwnd = self.xid_to_hwnd.get(alt_xid)
                        if hwnd:
                            self.bridge._emit("toggle", hwnd)

                    elif msg_type == self.atom_close_window:
                        hwnd = self.xid_to_hwnd.get(target_xid)
                        if hwnd:
                            self.bridge._emit("close", hwnd)

                    elif msg_type == self.atom_wm_protocols:
                        if hasattr(event, "data") and len(event.data.data32) > 0:
                            proto = event.data.data32[0]
                            if proto == self.atom_wm_delete_window:
                                hwnd = self.xid_to_hwnd.get(target_xid)
                                if hwnd:
                                    self.bridge._emit("close", hwnd)
            except Exception:
                break


class TaskBridge:
    def __init__(self) -> None:
        self.tasks: Dict[int, Dict[str, Any]] = {}
        self.lock = threading.RLock()
        self.running = True

        self.state_dir = os.path.expanduser("~/.local/state/nt-plasma")
        os.makedirs(self.state_dir, exist_ok=True)
        self.tasks_file = os.path.join(self.state_dir, "tasks.json")
        self.sock_path = os.path.join(self.state_dir, "bridge.sock")

        # Start socket server for plasmoid actions
        self.server_thread = threading.Thread(target=self._run_socket_server, daemon=True)
        self.server_thread.start()

        # Initial flush of empty task list
        self._flush_tasks_to_disk()

        # D-Bus KWin service for ShowDesktop / MinimizeAll integration
        self.kwin_service: Optional[KWinDbusService] = None
        self._start_dbus_kwin()

        # X11 EWMH Stub Manager for native KDE Task Manager integration
        self.x11_stubs = X11StubManager(self)
        self.x11_stubs.start()

    def _ensure_dbus_env(self) -> None:
        addr = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
        sock = addr.replace("unix:path=", "").split(",")[0] if addr else ""
        if sock and os.path.exists(sock):
            return
        home = os.environ.get("HOME", "/home/jace479")
        env_file = os.path.join(home, ".local", "state", "nt-plasma", "dbus.env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        if line.startswith("export DBUS_SESSION_BUS_ADDRESS="):
                            val = line.split("=", 1)[1].strip().strip("'\"")
                            os.environ["DBUS_SESSION_BUS_ADDRESS"] = val
                            return
            except Exception:
                pass
        for p in glob.glob("/proc/[0-9]*/cmdline"):
            try:
                with open(p, "rb") as f:
                    cmd = f.read().decode("utf-8", errors="ignore")
                if "plasmashell" in cmd:
                    pid = p.split("/")[2]
                    with open(f"/proc/{pid}/environ", "rb") as f:
                        env = f.read().decode("utf-8", errors="ignore").split("\0")
                    for var in env:
                        if var.startswith("DBUS_SESSION_BUS_ADDRESS="):
                            os.environ["DBUS_SESSION_BUS_ADDRESS"] = var.split("=", 1)[1]
                            return
            except Exception:
                continue

    def _start_dbus_kwin(self) -> None:
        if not HAS_DBUS:
            return
        self._ensure_dbus_env()
        try:
            DBusGMainLoop(set_as_default=True)
            bus = dbus.SessionBus()
            self.kwin_service = KWinDbusService(bus, self)
            loop = GLib.MainLoop()
            threading.Thread(target=loop.run, daemon=True).start()
        except Exception as e:
            sys.stderr.write(f"[task-bridge] Failed to register org.kde.KWin on D-Bus: {e}\n")

    def _run_socket_server(self) -> None:
        if os.path.exists(self.sock_path):
            try:
                os.unlink(self.sock_path)
            except OSError:
                pass

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(self.sock_path)
        server.listen(16)

        while self.running:
            try:
                conn, _ = server.accept()
                threading.Thread(target=self._handle_socket_client, args=(conn,), daemon=True).start()
            except Exception:
                break

    def _handle_socket_client(self, conn: socket.socket) -> None:
        with conn:
            try:
                data = conn.recv(4096).decode("utf-8")
                if not data:
                    return
                for line in data.strip().split("\n"):
                    if not line:
                        continue
                    msg = json.loads(line)
                    action = msg.get("action")
                    hwnd = msg.get("hwnd")
                    if action:
                        if action in ("show_desktop", "minimize_all", "restore_all"):
                            if self.kwin_service:
                                showing = (action != "restore_all")
                                self.kwin_service.set_showing_desktop(showing)
                        self._emit(action, hwnd)
            except Exception as e:
                sys.stderr.write(f"[task-bridge] Socket client error: {e}\n")

    def _emit(self, action: str, hwnd: Optional[int] = None) -> None:
        payload: Dict[str, Any] = {"action": action}
        if hwnd is not None:
            payload["hwnd"] = hwnd
        sys.stdout.write(json.dumps(payload) + "\n")
        sys.stdout.flush()

    def _flush_tasks_to_disk(self) -> None:
        with self.lock:
            tasks_list = list(self.tasks.values())

        tmp_file = f"{self.tasks_file}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            os.makedirs(self.state_dir, exist_ok=True)
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(tasks_list, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, self.tasks_file)
        except Exception as e:
            try:
                if os.path.exists(tmp_file):
                    os.unlink(tmp_file)
            except Exception:
                pass
            sys.stderr.write(f"[task-bridge] Failed to write tasks.json: {e}\n")
            sys.stderr.flush()

    def _handle_host_command(self, cmd: Dict[str, Any]) -> None:
        op = cmd.get("op")
        if not op:
            return

        if op == "add":
            hwnd = cmd.get("hwnd")
            if hwnd:
                app_id = cmd.get("appId", "windows-app")
                process = cmd.get("process", "app")
                title = cmd.get("title", "Windows Application")
                pid = cmd.get("pid", 1000)
                minimized = cmd.get("minimized", False)
                active = cmd.get("active", False)
                with self.lock:
                    self.tasks[hwnd] = {
                        "hwnd": hwnd,
                        "title": title,
                        "app_id": app_id,
                        "process": process,
                        "icon": resolve_icon(app_id, process, title),
                        "pid": pid,
                        "minimized": minimized,
                        "active": active,
                    }
                self._flush_tasks_to_disk()
                self.x11_stubs.add_window(
                    hwnd=hwnd,
                    title=title,
                    app_id=app_id,
                    process=process,
                    pid=pid,
                    minimized=minimized,
                    active=active,
                )

        elif op == "update":
            hwnd = cmd.get("hwnd")
            if hwnd:
                title_val = cmd.get("title")
                minimized_val = cmd.get("minimized")
                with self.lock:
                    if hwnd in self.tasks:
                        if title_val is not None:
                            self.tasks[hwnd]["title"] = title_val
                        if minimized_val is not None:
                            self.tasks[hwnd]["minimized"] = minimized_val
                self._flush_tasks_to_disk()
                self.x11_stubs.update_window(hwnd, title=title_val, minimized=minimized_val)

        elif op == "remove":
            hwnd = cmd.get("hwnd")
            if hwnd:
                with self.lock:
                    self.tasks.pop(hwnd, None)
                self._flush_tasks_to_disk()
                self.x11_stubs.remove_window(hwnd)

        elif op == "active":
            hwnd = cmd.get("hwnd")
            with self.lock:
                for h, t in self.tasks.items():
                    t["active"] = (h == hwnd)
            self._flush_tasks_to_disk()
            if hwnd:
                self.x11_stubs.set_active_window(hwnd)

        elif op == "sync":
            new_tasks_list = cmd.get("tasks", [])
            new_dict = {}
            for t in new_tasks_list:
                hwnd = t.get("hwnd")
                if not hwnd:
                    continue
                app_id = t.get("appId", "windows-app")
                process = t.get("process", "app")
                title = t.get("title", "Windows Application")
                new_dict[hwnd] = {
                    "hwnd": hwnd,
                    "title": title,
                    "app_id": app_id,
                    "process": process,
                    "icon": resolve_icon(app_id, process, title),
                    "pid": t.get("pid", 1000),
                    "minimized": t.get("minimized", False),
                    "active": t.get("active", False),
                }
            with self.lock:
                self.tasks = new_dict
            self._flush_tasks_to_disk()
            self.x11_stubs.sync_all(self.tasks)

        elif op == "notify":
            self._ensure_dbus_env()
            title = cmd.get("title", "ntKDE")
            body = cmd.get("body", "")
            app_name = cmd.get("app_name", "Windows")
            icon = cmd.get("icon", "preferences-desktop-notification")
            timeout = str(cmd.get("timeout", 5000))
            try:
                subprocess.Popen([
                    "gdbus", "call", "--session",
                    "--dest", "org.freedesktop.Notifications",
                    "--object-path", "/org/freedesktop/Notifications",
                    "--method", "org.freedesktop.Notifications.Notify",
                    app_name, "0", icon, title, body, "[]", "{}", timeout
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                sys.stderr.write(f"[task-bridge] Failed to dispatch notification: {e}\n")

        elif op == "kickoff":
            self._ensure_dbus_env()
            try:
                subprocess.Popen([
                    "gdbus", "call", "--session",
                    "--dest", "org.kde.plasmashell",
                    "--object-path", "/PlasmaShell",
                    "--method", "org.kde.PlasmaShell.activateLauncherMenu"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        elif op == "krunner":
            self._ensure_dbus_env()
            try:
                res = subprocess.run([
                    "gdbus", "call", "--session",
                    "--dest", "org.kde.krunner",
                    "--object-path", "/App",
                    "--method", "org.kde.krunner.App.display"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)
                if res.returncode != 0:
                    subprocess.Popen(["krunner"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                try:
                    subprocess.Popen(["krunner"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass

        elif op == "volume":
            self._ensure_dbus_env()
            percent = int(cmd.get("percent", 50))
            try:
                subprocess.Popen([
                    "gdbus", "call", "--session",
                    "--dest", "org.kde.plasmashell",
                    "--object-path", "/org/kde/osdService",
                    "--method", "org.kde.osdService.volumeChanged",
                    str(percent)
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        elif op == "fullscreen":
            is_active = bool(cmd.get("active", False))
            fs_file = os.path.join(self.state_dir, "fullscreen.json")
            tmp_fs = fs_file + ".tmp"
            try:
                with open(tmp_fs, "w", encoding="utf-8") as f:
                    json.dump({"fullscreen": is_active}, f)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_fs, fs_file)
            except Exception as e:
                sys.stderr.write(f"[task-bridge] Failed to write fullscreen.json: {e}\n")

        elif op == "media_osd":
            self._ensure_dbus_env()
            icon = cmd.get("icon", "media-playback-start")
            text = cmd.get("text", "")
            try:
                subprocess.Popen([
                    "gdbus", "call", "--session",
                    "--dest", "org.kde.plasmashell",
                    "--object-path", "/org/kde/osdService",
                    "--method", "org.kde.osdService.showText",
                    icon, text
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def run(self) -> None:
        sys.stderr.write("[task-bridge] ntKDE Native Task Manager Bridge started successfully.\n")
        sys.stderr.flush()

        # Stdio reader loop from Windows host
        try:
            while self.running:
                line = sys.stdin.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    cmd = json.loads(line)
                    self._handle_host_command(cmd)
                except json.JSONDecodeError as err:
                    sys.stderr.write(f"[task-bridge] Failed to decode host JSON: {err}\n")
                    sys.stderr.flush()
                    continue
        except Exception as e:
            sys.stderr.write(f"[task-bridge] Stdio reader loop exception: {e}\n")
            sys.stderr.flush()
        finally:
            self.running = False
            if hasattr(self, "x11_stubs"):
                self.x11_stubs.running = False
            if os.path.exists(self.sock_path):
                try:
                    os.unlink(self.sock_path)
                except OSError:
                    pass


def main() -> None:
    bridge = TaskBridge()
    try:
        bridge.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
