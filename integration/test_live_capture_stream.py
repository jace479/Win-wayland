import os
import struct
import subprocess
import sys
import time
import unittest

MAGIC_NTFR = 0x4E545246


class LiveCaptureStreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Locate ntkde binary
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.ntkde_exe = os.path.join(repo_root, "bin", "ntkde.exe")
        if not os.path.exists(cls.ntkde_exe):
            cls.ntkde_exe = os.path.join(repo_root, "host", "DesktopSurfaceHost", "bin", "Release", "net8.0-windows", "ntkde.exe")

    def test_live_streamer_frames_and_input(self):
        """Test Windows host capture streamer over Windows Named Pipe (Zero-TCP)."""
        if not os.path.exists(self.ntkde_exe):
            self.skipTest(f"ntkde executable not found at {self.ntkde_exe}")

        # Clean up any stale notepad instances before test
        subprocess.run(["taskkill", "/F", "/IM", "notepad.exe"], capture_output=True)

        # Launch notepad to have a guaranteed target window
        np_proc = subprocess.Popen(["notepad.exe"])
        try:
            time.sleep(1.2)

            # Start ntkde compose notepad with --host-only (serves named pipe)
            streamer_proc = subprocess.Popen(
                [self.ntkde_exe, "compose", "notepad", "--host-only"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            try:
                # Connect to Windows Named Pipe (Zero-TCP)
                pipe_path = r"\\.\pipe\ntkde_surface_notepad"
                pipe = None
                for _ in range(30):
                    time.sleep(0.3)
                    try:
                        pipe = open(pipe_path, "r+b", buffering=0)
                        break
                    except (FileNotFoundError, OSError):
                        pass

                self.assertIsNotNone(pipe, f"Could not connect to Named Pipe at {pipe_path}")

                # Read at least 2 frames and verify header + payload
                header_struct = struct.Struct("<iiiii")
                for frame_idx in range(2):
                    header_bytes = self._recv_exact(pipe, header_struct.size)
                    self.assertIsNotNone(header_bytes, f"Failed to receive frame header {frame_idx}")
                    window_id, width, height, payload_length, magic = header_struct.unpack(header_bytes)

                    self.assertEqual(magic, MAGIC_NTFR, "Magic bytes must match MAGIC_NTFR (0x4E545246)")
                    self.assertGreater(width, 0, "Captured width must be > 0")
                    self.assertGreater(height, 0, "Captured height must be > 0")
                    self.assertEqual(payload_length, width * height * 3, "Payload length must match width * height * 3 (24bpp)")

                    payload = self._recv_exact(pipe, payload_length)
                    self.assertIsNotNone(payload, f"Failed to receive pixel payload for frame {frame_idx}")
                    self.assertEqual(len(payload), payload_length)

                # Send test pointer move and verify no crash
                pipe.write(b"INPUT|POINTER|move|50|50\n")
                time.sleep(0.1)

                # Send mouse wheel scroll
                pipe.write(b"INPUT|POINTER|wheel|50|50|120\n")
                time.sleep(0.1)

                # Send double-click
                pipe.write(b"INPUT|POINTER|dblclk|50|50|left\n")
                time.sleep(0.1)

                # Send bidirectional resize negotiation
                pipe.write(b"INPUT|RESIZE|640|480\n")
                time.sleep(0.2)

                # Send window state commands
                pipe.write(b"INPUT|STATE|minimize\n")
                time.sleep(0.1)
                pipe.write(b"INPUT|STATE|restore\n")
                time.sleep(0.1)

                # Send close command
                pipe.write(b"INPUT|CLOSE\n")
                time.sleep(0.2)
                pipe.close()

            finally:
                streamer_proc.terminate()
                try:
                    streamer_proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    streamer_proc.kill()
                    streamer_proc.wait()
        finally:
            if np_proc.poll() is None:
                np_proc.kill()
            subprocess.run(["taskkill", "/F", "/IM", "notepad.exe"], capture_output=True)

    def test_compose_list_discovers_windows(self):
        """Verify 'ntkde compose --list' correctly enumerates composable windows."""
        if not os.path.exists(self.ntkde_exe):
            self.skipTest(f"ntkde executable not found at {self.ntkde_exe}")

        result = subprocess.run(
            [self.ntkde_exe, "compose", "--list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, f"compose --list failed: {result.stderr}")
        self.assertIn("composable top-level windows", result.stdout)
        self.assertIn("HWND", result.stdout)
        self.assertIn("PID", result.stdout)
        self.assertIn("PROCESS", result.stdout)
        self.assertIn("TITLE", result.stdout)

    def test_wsl_presenter_receives_live_stream(self):
        """Test end-to-end Windows host to WSL KDE presenter over in-kernel stdio pipe (Zero-TCP)."""
        if not os.path.exists(self.ntkde_exe):
            self.skipTest(f"ntkde executable not found at {self.ntkde_exe}")

        # Clean up any stale notepad instances before test
        subprocess.run(["taskkill", "/F", "/IM", "notepad.exe"], capture_output=True)

        np_proc = subprocess.Popen(["notepad.exe"])
        try:
            time.sleep(1.2)

            result = subprocess.run(
                [self.ntkde_exe, "compose", "notepad", "--verify-frames", "2"],
                capture_output=True,
                text=True,
                timeout=25,
            )
            self.assertEqual(result.returncode, 0, f"ntkde compose failed: {result.stdout} {result.stderr}")
            self.assertIn("SUCCESS: verified 2 frames", result.stdout + result.stderr)
        finally:
            if np_proc.poll() is None:
                np_proc.kill()
            subprocess.run(["taskkill", "/F", "/IM", "notepad.exe"], capture_output=True)

    def test_foreign_presenter_coordinate_mapping(self):
        """Verify ForeignSurfaceWidget accurately maps pointer coordinates when scaled."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "wsl"))
        import foreign_window_presenter

        widget = foreign_window_presenter.ForeignSurfaceWidget()
        # Mock width, height, and image
        widget.width = lambda: 1600
        widget.height = lambda: 1200
        class DummyImage:
            def isNull(self): return False
            def width(self): return 800
            def height(self): return 600
        widget.image = DummyImage()

        # Click at center of 1600x1200 window should map to (400, 300) in 800x600 Windows app
        mapped_x, mapped_y = widget._map_coords(800, 600)
        self.assertEqual(mapped_x, 400)
        self.assertEqual(mapped_y, 300)

        # 1:1 test
        widget.width = lambda: 800
        widget.height = lambda: 600
        mapped_x, mapped_y = widget._map_coords(123, 456)
        self.assertEqual(mapped_x, 123)
        self.assertEqual(mapped_y, 456)

    @staticmethod
    def _recv_exact(stream, length):
        buffer = bytearray(length)
        view = memoryview(buffer)
        received = 0
        while received < length:
            try:
                n = stream.readinto(view[received:])
                if n == 0 or n is None:
                    return None
                received += n
            except OSError:
                return None
        return bytes(buffer)


if __name__ == "__main__":
    unittest.main()
