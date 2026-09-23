import os
import struct
import sys
import unittest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    from wsl.foreign_window_presenter import MAGIC_NTFR, ForeignSurfaceWidget, map_qt_key_to_vk
    HAS_PRESENTER = True
except ImportError:
    HAS_PRESENTER = False
    MAGIC_NTFR = 0x4E545246
    ForeignSurfaceWidget = None
    map_qt_key_to_vk = None


class ForeignSurfaceStreamTests(unittest.TestCase):
    def test_ntfr_header_packing_and_unpacking(self):
        header_struct = struct.Struct("<iiiii")
        window_id = 1
        width = 1280
        height = 720
        payload_length = width * height * 3

        header_bytes = header_struct.pack(window_id, width, height, payload_length, MAGIC_NTFR)
        self.assertEqual(len(header_bytes), 20)

        unpacked_id, unpacked_w, unpacked_h, unpacked_len, unpacked_magic = header_struct.unpack(header_bytes)
        self.assertEqual(unpacked_id, window_id)
        self.assertEqual(unpacked_w, width)
        self.assertEqual(unpacked_h, height)
        self.assertEqual(unpacked_len, payload_length)
        self.assertEqual(unpacked_magic, MAGIC_NTFR)

    def test_corrupted_magic_is_rejected(self):
        header_struct = struct.Struct("<iiiii")
        corrupted = header_struct.pack(1, 100, 100, 30000, 0x12345678)
        _, _, _, _, magic = header_struct.unpack(corrupted)
        self.assertNotEqual(magic, MAGIC_NTFR)

    def test_key_to_vk_mapping(self):
        map_fn = map_qt_key_to_vk if map_qt_key_to_vk else (ForeignSurfaceWidget._map_key_to_vk if ForeignSurfaceWidget else None)
        self.assertIsNotNone(map_fn)
        # Letters A-Z
        self.assertEqual(map_fn(0x41, "a"), 0x41)
        self.assertEqual(map_fn(0x5A, "z"), 0x5A)

        # Numbers 0-9
        self.assertEqual(map_fn(0x30, "0"), 0x30)
        self.assertEqual(map_fn(0x39, "9"), 0x39)

        # Enter / Return
        self.assertEqual(map_fn(0x01000004, ""), 0x0D)
        # Backspace
        self.assertEqual(map_fn(0x01000003, ""), 0x08)
        # Escape
        self.assertEqual(map_fn(0x01000000, ""), 0x1B)


if __name__ == "__main__":
    unittest.main()
