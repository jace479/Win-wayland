import unittest

from integration.foreign_surface import WindowMetadata
from integration.surface_events import SurfaceEventFactory


class SurfaceEventFactoryTests(unittest.TestCase):
    def setUp(self):
        self.metadata = WindowMetadata("w1", "windows:code", "Code - WinKDE", 800, 600, 2, "code")

    def test_created_and_updated_events_preserve_identity_and_names(self):
        created = SurfaceEventFactory.created(self.metadata)
        updated = SurfaceEventFactory.updated(self.metadata)

        self.assertEqual(created.operation, "window.created")
        self.assertEqual(updated.payload["title"], "Code - WinKDE")
        self.assertEqual(updated.payload["icon"], "code")
        self.assertEqual(updated.payload["monitor"], 2)

    def test_destroyed_event_contains_only_surface_id(self):
        destroyed = SurfaceEventFactory.destroyed("w1")

        self.assertEqual(destroyed.payload, {"window": "w1"})
        self.assertNotIn("hwnd", destroyed.payload)


if __name__ == "__main__":
    unittest.main()