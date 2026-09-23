import unittest

from integration.bridge_protocol import ProtocolError
from integration.desktop_surface_registry import DesktopSurfaceRegistry
from integration.foreign_surface import ForeignSurface, WindowMetadata


class DesktopSurfaceRegistryTests(unittest.TestCase):
    def test_registry_preserves_independent_window_names_and_frame_state(self):
        registry = DesktopSurfaceRegistry()
        first = ForeignSurface(WindowMetadata("w2", "windows:calc", "Calculator", 400, 300, 2, "calc"))
        second = ForeignSurface(WindowMetadata("w1", "windows:code", "Code", 800, 600, 1, "code"))
        second.submit_frame(2, 1, bytes((1, 2, 3)) * 2)
        registry.add_foreign_surface(first)
        registry.add_foreign_surface(second)

        self.assertEqual(
            [(record.surface_id, record.title, record.has_frame) for record in registry.records()],
            [("w1", "Code", True), ("w2", "Calculator", False)],
        )

    def test_pointer_request_targets_registered_surface(self):
        registry = DesktopSurfaceRegistry()
        registry.add_foreign_surface(
            ForeignSurface(WindowMetadata("w1", "windows:code", "Code", 800, 600, 1))
        )

        self.assertEqual(
            registry.pointer_request("w1", 100, 200, "move"),
            {"window": "w1", "event": "move", "x": 100, "y": 200},
        )
        with self.assertRaises(ProtocolError):
            registry.pointer_request("missing", 1, 1, "move")

    def test_duplicate_surfaces_are_rejected(self):
        registry = DesktopSurfaceRegistry()
        surface = ForeignSurface(WindowMetadata("w1", "windows:code", "Code", 800, 600, 1))
        registry.add_foreign_surface(surface)
        with self.assertRaises(ProtocolError):
            registry.add_foreign_surface(surface)


if __name__ == "__main__":
    unittest.main()