"""Central middleware service coordinating Windows NT host and KDE Plasma."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .app_catalog import ApplicationCatalog
from .bridge_broker import HostBroker
from .bridge_protocol import Message, ProtocolError
from .bridge_session import BridgeSession
from .desktop_surface_registry import DesktopSurfaceRegistry, DesktopSurfaceRecord
from .foreign_surface import ForeignSurface, WindowMetadata
from .shell_lifecycle import NtKdeShellLifecycle


@dataclass(frozen=True)
class NotificationPayload:
    title: str
    body: str
    urgency: str = "normal"
    app_name: str = "ntKDE"


class ShellMiddleware:
    """Coordinates application launching, window tracking, notifications, and shell lifecycle."""

    def __init__(
        self,
        session: BridgeSession,
        catalog: ApplicationCatalog,
        lifecycle: NtKdeShellLifecycle | None = None,
        registry: DesktopSurfaceRegistry | None = None,
        launcher_fn: Callable[[str], bool] | None = None,
        notifier_fn: Callable[[NotificationPayload], bool] | None = None,
    ) -> None:
        self.session = session
        self.catalog = catalog
        self.lifecycle = lifecycle or NtKdeShellLifecycle()
        self.registry = registry or DesktopSurfaceRegistry()
        self.launcher_fn = launcher_fn or self._default_launcher
        self.notifier_fn = notifier_fn or self._default_notifier
        desktop_apps = catalog.list_for_desktop()
        self.broker = HostBroker(
            session=self.session,
            application_allow_list={app["id"]: catalog.resolve(app["id"]).executable for app in desktop_apps},
            desktop_catalog=catalog,
        )

    def dispatch(self, message: Message) -> dict[str, Any]:
        """Process incoming requests from KDE or Host."""
        if message.kind != "request":
            raise ProtocolError("ShellMiddleware accepts request messages only")

        self.session.require_ready()
        operation = message.operation

        if operation == "app.launch":
            app_id = message.payload.get("application")
            if not isinstance(app_id, str) or not app_id:
                raise ProtocolError("app.launch requires an application identifier")
            success = self.launcher_fn(app_id)
            return {
                "operation": "app.launch.result",
                "application": app_id,
                "status": "launched" if success else "failed",
            }

        if operation == "app.list":
            return {
                "operation": "app.list.result",
                "applications": self.catalog.list_for_desktop(),
            }

        if operation == "window.event":
            return self._handle_window_event(message.payload)

        if operation == "window.list":
            return {
                "operation": "window.list.result",
                "surfaces": [record.surface_id for record in self.registry.records()],
            }

        if operation == "notify.send":
            title = message.payload.get("title", "")
            body = message.payload.get("body", "")
            urgency = message.payload.get("urgency", "normal")
            app_name = message.payload.get("app_name", "ntKDE")
            if not title and not body:
                raise ProtocolError("Notification requires title or body")
            delivered = self.notifier_fn(NotificationPayload(title=title, body=body, urgency=urgency, app_name=app_name))
            return {
                "operation": "notify.send.result",
                "status": "delivered" if delivered else "failed",
            }

        if operation == "lifecycle.status":
            return {
                "operation": "lifecycle.status.result",
                "lifecycle": self.lifecycle.snapshot(),
            }

        if operation == "places.sync":
            places_path = Path.home() / ".local/share/user-places.xbel"
            mount_root = Path("/mnt")
            count = self.sync_dolphin_places(places_path, mount_root)
            return {
                "operation": "places.sync.result",
                "drives_synced": count,
            }

        broker_result = self.broker.dispatch(message)
        return {
            "operation": broker_result.operation,
            **dict(broker_result.payload),
        }

    def _handle_window_event(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        event_type = payload.get("type")
        surface_id = payload.get("surface_id")
        if not event_type or not surface_id:
            raise ProtocolError("window.event requires type and surface_id")

        if event_type == "window.created":
            metadata = WindowMetadata(
                window_id=surface_id,
                application_id=payload.get("application_id", "unknown"),
                title=payload.get("title", "Untitled"),
                monitor=int(payload.get("monitor", 1)),
                width=int(payload.get("width", 800)),
                height=int(payload.get("height", 600)),
                icon=payload.get("icon"),
            )
            self.registry.add_foreign_surface(ForeignSurface(metadata))
            return {"operation": "window.event.result", "status": "registered", "surface_id": surface_id}

        if event_type == "window.destroyed":
            self.registry.remove(surface_id)
            return {"operation": "window.event.result", "status": "removed", "surface_id": surface_id}

        if event_type == "window.focused":
            return {"operation": "window.event.result", "status": "focused", "surface_id": surface_id}

        raise ProtocolError(f"Unknown window event type: {event_type}")

    def sync_dolphin_places(self, places_path: Path, mount_root: Path) -> int:
        """Invokes the Dolphin drive places synchronizer."""
        try:
            from wsl import sync_windows_drives_to_dolphin  # type: ignore
            return sync_windows_drives_to_dolphin.synchronize(places_path, mount_root)
        except (ImportError, Exception):
            import string
            import xml.etree.ElementTree as ET
            xbel_ns = "http://www.freedesktop.org/standards/desktop-bookmarks"
            ET.register_namespace("", xbel_ns)

            drives = [
                (letter, mount_root / letter.lower())
                for letter in string.ascii_uppercase
                if (mount_root / letter.lower()).is_dir()
            ]

            if places_path.exists():
                tree = ET.parse(places_path)
                root = tree.getroot()
            else:
                root = ET.Element(f"{{{xbel_ns}}}xbel", {"version": "1.0"})
                tree = ET.ElementTree(root)

            for bookmark in list(root):
                if bookmark.tag == f"{{{xbel_ns}}}bookmark" and bookmark.get("ntkde-managed") == "windows-drive":
                    root.remove(bookmark)

            for letter, path in drives:
                bookmark = ET.SubElement(
                    root,
                    f"{{{xbel_ns}}}bookmark",
                    {"href": path.resolve().as_uri(), "ntkde-managed": "windows-drive"},
                )
                ET.SubElement(bookmark, f"{{{xbel_ns}}}title").text = f"{letter}:"

            places_path.parent.mkdir(parents=True, exist_ok=True)
            tree.write(places_path, encoding="utf-8", xml_declaration=True)
            return len(drives)

    def _default_launcher(self, app_id: str) -> bool:
        try:
            return bool(self.catalog.resolve(app_id))
        except ProtocolError:
            return False

    def _default_notifier(self, notification: NotificationPayload) -> bool:
        try:
            subprocess.run(
                ["notify-send", "-a", notification.app_name, "-u", notification.urgency, notification.title, notification.body],
                check=True,
                capture_output=True,
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False
