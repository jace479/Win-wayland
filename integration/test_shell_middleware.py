import unittest
from pathlib import Path
import tempfile

from integration.app_catalog import ApplicationCatalog, ApplicationEntry
from integration.bridge_protocol import Message, ProtocolError
from integration.bridge_session import BridgeSession
from integration.desktop_surface_registry import DesktopSurfaceRegistry
from integration.shell_lifecycle import NtKdeShellLifecycle
from integration.shell_middleware import NotificationPayload, ShellMiddleware


class ShellMiddlewareTests(unittest.TestCase):
    def setUp(self):
        self.session = BridgeSession()
        self.session.connect()
        self.session.authenticate()
        self.session.mark_ready()

        self.catalog = ApplicationCatalog(
            (
                ApplicationEntry(
                    application_id="notepad",
                    display_name="Notepad",
                    executable="C:\\Windows\\notepad.exe",
                    origin="windows",
                    category="Utility",
                ),
                ApplicationEntry(
                    application_id="steam",
                    display_name="Steam",
                    executable="C:\\Program Files (x86)\\Steam\\steam.exe",
                    origin="windows",
                    category="Game",
                ),
            )
        )
        self.lifecycle = NtKdeShellLifecycle()
        self.registry = DesktopSurfaceRegistry()
        self.launched = []
        self.notifications = []

        self.middleware = ShellMiddleware(
            session=self.session,
            catalog=self.catalog,
            lifecycle=self.lifecycle,
            registry=self.registry,
            launcher_fn=lambda app: (self.launched.append(app) or True),
            notifier_fn=lambda notif: (self.notifications.append(notif) or True),
        )

    def test_app_launch_dispatches_successfully(self):
        msg = Message(
            version=1,
            message_id="msg-1",
            kind="request",
            operation="app.launch",
            payload={"application": "notepad"},
        )
        result = self.middleware.dispatch(msg)
        self.assertEqual(result["operation"], "app.launch.result")
        self.assertEqual(result["status"], "launched")
        self.assertIn("notepad", self.launched)

    def test_app_list_returns_catalog(self):
        msg = Message(version=1, message_id="msg-2", kind="request", operation="app.list", payload={})
        result = self.middleware.dispatch(msg)
        self.assertEqual(result["operation"], "app.list.result")
        self.assertEqual(len(result["applications"]), 2)

    def test_window_events_track_in_registry(self):
        create_msg = Message(
            version=1,
            message_id="msg-3",
            kind="request",
            operation="window.event",
            payload={
                "type": "window.created",
                "surface_id": "win-101",
                "application_id": "notepad",
                "title": "Untitled - Notepad",
                "monitor": 1,
            },
        )
        self.middleware.dispatch(create_msg)
        self.assertIsNotNone(self.registry.surface("win-101"))

        list_msg = Message(version=1, message_id="msg-4", kind="request", operation="window.list", payload={})
        list_result = self.middleware.dispatch(list_msg)
        self.assertIn("win-101", list_result["surfaces"])

        destroy_msg = Message(
            version=1,
            message_id="msg-5",
            kind="request",
            operation="window.event",
            payload={"type": "window.destroyed", "surface_id": "win-101"},
        )
        self.middleware.dispatch(destroy_msg)
        with self.assertRaises(ProtocolError):
            self.registry.surface("win-101")

    def test_notification_delivery(self):
        msg = Message(
            version=1,
            message_id="msg-6",
            kind="request",
            operation="notify.send",
            payload={"title": "Test Title", "body": "Test Message", "urgency": "critical"},
        )
        result = self.middleware.dispatch(msg)
        self.assertEqual(result["operation"], "notify.send.result")
        self.assertEqual(result["status"], "delivered")
        self.assertEqual(len(self.notifications), 1)
        self.assertEqual(self.notifications[0].title, "Test Title")
        self.assertEqual(self.notifications[0].urgency, "critical")

    def test_lifecycle_status(self):
        msg = Message(version=1, message_id="msg-7", kind="request", operation="lifecycle.status", payload={})
        result = self.middleware.dispatch(msg)
        self.assertEqual(result["operation"], "lifecycle.status.result")
        self.assertIn("state", result["lifecycle"])

    def test_dolphin_places_sync(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_places = Path(temp_dir) / "places.xbel"
            mount_root = Path(temp_dir) / "mnt"
            (mount_root / "c").mkdir(parents=True)

            count = self.middleware.sync_dolphin_places(temp_places, mount_root)
            self.assertEqual(count, 1)
            content = temp_places.read_text(encoding="utf-8")
            self.assertIn("C:", content)


if __name__ == "__main__":
    unittest.main()
