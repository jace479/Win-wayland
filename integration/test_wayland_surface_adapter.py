import unittest

from integration.desktop_surface_registry import DesktopSurfaceRegistry
from integration.foreign_surface import ForeignSurface, WindowMetadata
from integration.wayland_surface_adapter import WaylandSurfaceAdapter


class WaylandSurfaceAdapterTests(unittest.TestCase):
    def setUp(self):
        registry = DesktopSurfaceRegistry()
        registry.add_foreign_surface(
            ForeignSurface(WindowMetadata("w1", "windows:code", "Code", 800, 600, 1, "code"))
        )
        self.adapter = WaylandSurfaceAdapter(registry)

    def test_synchronize_creates_named_role(self):
        roles = self.adapter.synchronize()

        self.assertEqual(len(roles), 1)
        self.assertEqual(roles[0].title, "Code")
        self.assertEqual(roles[0].icon, "code")

    def test_frame_descriptor_and_pointer_use_surface_id(self):
        self.adapter.synchronize()

        self.assertEqual(
            self.adapter.frame_descriptor("w1"),
            {"surface": "w1", "width": 800, "height": 600, "has_frame": False, "format": "BGR24"},
        )
        self.assertEqual(self.adapter.pointer("w1", 12, 24, "move")["window"], "w1")


if __name__ == "__main__":
    unittest.main()