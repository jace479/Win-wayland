import unittest

from integration.bridge_protocol import ProtocolError
from integration.foreign_surface import ForeignSurface, WindowMetadata


class ForeignSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.surface = ForeignSurface(WindowMetadata("w1", "windows:code", "Code", 800, 600, 1))

    def test_frame_requires_matching_dimensions(self):
        pixels = bytes((20, 40, 60)) * (320 * 200)
        self.surface.submit_frame(320, 200, pixels)
        self.assertEqual(self.surface.frame, pixels)
        with self.assertRaises(ProtocolError):
            self.surface.submit_frame(320, 200, b"short")

    def test_pointer_event_is_clamped(self):
        self.assertEqual(
            self.surface.pointer_event(-2, 700, "press"),
            {"window": "w1", "event": "press", "x": 0, "y": 599},
        )

    def test_identity_cannot_change(self):
        with self.assertRaises(ProtocolError):
            self.surface.update_metadata(WindowMetadata("w2", "windows:code", "Code", 800, 600, 1))

    def test_unknown_pointer_event_is_rejected(self):
        with self.assertRaises(ProtocolError):
            self.surface.pointer_event(1, 1, "shell-command")

    def test_presentation_keeps_application_and_window_names(self):
        self.surface.update_metadata(
            WindowMetadata("w1", "windows:code", "bridge_protocol.py - WinKDE", 800, 600, 1, "code")
        )

        self.assertEqual(
            self.surface.presentation(),
            {
                "window": "w1",
                "application": "windows:code",
                "title": "bridge_protocol.py - WinKDE",
                "icon": "code",
                "monitor": 1,
                "width": 800,
                "height": 600,
            },
        )

    def test_keyboard_and_focus_events_are_typed(self):
        self.assertEqual(
            self.surface.keyboard_event("KeyS", "press", ("CTRL",)),
            {"window": "w1", "event": "press", "key": "KeyS", "modifiers": ["CTRL"]},
        )
        self.assertEqual(self.surface.focus_event(True), {"window": "w1", "focused": True})
        with self.assertRaises(ProtocolError):
            self.surface.keyboard_event("", "press")


if __name__ == "__main__":
    unittest.main()