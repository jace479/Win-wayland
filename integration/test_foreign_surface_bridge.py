import unittest

from integration.bridge_protocol import Message, ProtocolError
from integration.foreign_surface_bridge import ForeignSurfaceBridge


class ForeignSurfaceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = ForeignSurfaceBridge()

    def test_window_created_event_creates_linux_surface(self):
        surface = self.bridge.accept_window_created(
            Message(
                1,
                "window-1",
                "event",
                "window.created",
                {
                    "window": "w1",
                    "application": "windows:code",
                    "title": "Code",
                    "width": 800,
                    "height": 600,
                    "monitor": 1,
                },
            )
        )

        self.assertEqual(surface.metadata.window_id, "w1")
        self.assertIn("w1", self.bridge.surfaces)

    def test_pointer_request_returns_host_window_id(self):
        self.bridge.accept_window_created(
            Message(1, "window-1", "event", "window.created", {
                "window": "w1", "application": "windows:code", "title": "Code",
                "width": 800, "height": 600, "monitor": 1,
            })
        )

        request = self.bridge.create_pointer_request("w1", 12, 24, "press")
        self.assertEqual(request.operation, "window.pointer")
        self.assertEqual(request.payload["window"], "w1")
        self.assertEqual(request.payload["x"], 12)

    def test_malformed_or_wrong_event_is_rejected(self):
        with self.assertRaises(ProtocolError):
            self.bridge.accept_window_created(
                Message(1, "window-1", "request", "window.created", {})
            )
        with self.assertRaises(ProtocolError):
            self.bridge.create_pointer_request("unknown", 1, 1, "move")

    def test_multiple_windows_keep_independent_names(self):
        for window_id, title in (("w2", "Calculator"), ("w1", "Code")):
            self.bridge.accept_window_created(
                Message(1, window_id, "event", "window.created", {
                    "window": window_id, "application": "windows:test", "title": title,
                    "width": 400, "height": 300, "monitor": 1,
                })
            )

        self.assertEqual([item["title"] for item in self.bridge.presentations()], ["Code", "Calculator"])

    def test_keyboard_and_focus_requests_keep_surface_identity(self):
        self.bridge.accept_window_created(
            Message(1, "window-1", "event", "window.created", {
                "window": "w1", "application": "windows:code", "title": "Code",
                "width": 800, "height": 600, "monitor": 1,
            })
        )
        keyboard = self.bridge.create_keyboard_request("w1", "KeyS", "press", ("CTRL",))
        focus = self.bridge.create_focus_request("w1", True)
        self.assertEqual(keyboard.operation, "window.keyboard")
        self.assertEqual(keyboard.payload["window"], "w1")
        self.assertEqual(focus.payload, {"window": "w1", "focused": True})


if __name__ == "__main__":
    unittest.main()