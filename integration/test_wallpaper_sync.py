import os
import unittest
import subprocess
from pathlib import Path

class WallpaperSyncTests(unittest.TestCase):
    def test_sync_script_exists(self):
        script = Path(__file__).resolve().parent.parent / "powershell" / "Sync-KdeWallpaper.ps1"
        self.assertTrue(script.exists(), "Sync-KdeWallpaper.ps1 should exist")

    def test_apply_wallpaper_binary_exists(self):
        binary = Path(__file__).resolve().parent.parent / "powershell" / "ApplyWallpaper.exe"
        self.assertTrue(binary.exists(), "ApplyWallpaper.exe should exist")

    def test_kde_wallpaper_resolution(self):
        target_file = Path(os.environ.get("LOCALAPPDATA", "")) / "nt-plasma" / "wallpaper.jpg"
        self.assertTrue(target_file.exists(), f"Cached wallpaper should exist at {target_file}")
        self.assertGreater(target_file.stat().st_size, 100000, "Cached wallpaper should be non-trivial image")

if __name__ == "__main__":
    unittest.main()
