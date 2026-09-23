import unittest

from integration.bridge_protocol import ProtocolError
from integration.desktop_surface_registry import DesktopSurfaceRegistry
from integration.foreign_surface import ForeignSurface, WindowMetadata
from integration.wayland_foreign_surface_protocol import WaylandForeignSurfaceProtocol


class WaylandForeignSurfaceProtocolTests(unittest.TestCase):
    def setUp(self):
        registry = DesktopSurfaceRegistry()
        registry.add_foreign_surface(
            ForeignSurface(WindowMetadata("w1", "windows:code", "Code", 2, 2, 1, "code"))
        )
        self.protocol = WaylandForeignSurfaceProtocol(registry)
        self.protocol.create_surface("w1")

    def test_client_attaches_ordered_frame_and_receives_events(self):
        self.protocol.set_metadata(
            "w1", WindowMetadata("w1", "windows:code", "Updated", 2, 2, 1, "code")
        )
        self.protocol.attach_frame("w1", 2, 2, 1, b"\x00" * 12)
        self.protocol.configure("w1", 4, 2, 2)
        self.protocol.focus("w1")

        self.assertEqual(
            [(event.name, event.payload) for event in self.protocol.events()],
            [("configure", {"serial": 4, "width": 2, "height": 2}), ("focus", {})],
        )

    def test_rejects_stale_frame_and_emits_rejection(self):
        self.protocol.attach_frame("w1", 2, 2, 3, b"\x00" * 12)

        with self.assertRaises(ProtocolError):
            self.protocol.attach_frame("w1", 2, 2, 3, b"\x00" * 12)

        event = self.protocol.events()[0]
        self.assertEqual(event.name, "frame_rejected")
        self.assertEqual(event.payload["sequence"], 3)


if __name__ == "__main__":
    unittest.main()