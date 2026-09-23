import unittest

from integration.bridge_protocol import ProtocolError
from integration.wayland_protocol import validate_frame_sequence, validate_surface_dimensions


class WaylandProtocolTests(unittest.TestCase):
    def test_frame_sequence_must_increase(self):
        validate_frame_sequence(None, 0)
        validate_frame_sequence(0, 1)
        with self.assertRaises(ProtocolError):
            validate_frame_sequence(1, 1)

    def test_surface_dimensions_are_bounded(self):
        validate_surface_dimensions(1920, 1080)
        with self.assertRaises(ProtocolError):
            validate_surface_dimensions(0, 1080)
        with self.assertRaises(ProtocolError):
            validate_surface_dimensions(20000, 1080)


if __name__ == "__main__":
    unittest.main()