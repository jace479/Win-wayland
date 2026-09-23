import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from integration.generate_kde_entries import generate_entries


class GenerateKdeEntriesTests(unittest.TestCase):
    def test_generates_windows_entry_with_kde_category_and_stable_id(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            catalog = root / "catalog.json"
            catalog.write_text(
                json.dumps(
                    [
                        {
                            "id": "windows:notepad",
                            "name": "Notepad",
                            "category": "Office",
                            "target": "C:\\Windows\\notepad.exe",
                            "icon": "C:\\Windows\\System32\\notepad.exe",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            output = root / "applications"

            self.assertEqual(generate_entries(catalog, output), 1)
            desktop = next(output.glob("*.desktop")).read_text(encoding="utf-8")

        self.assertIn("Name=Notepad", desktop)
        self.assertIn("Exec=/opt/nt-plasma/bin/launch-windows-app windows:notepad", desktop)
        self.assertIn("Categories=Office;", desktop)
        self.assertNotIn("Categories=Windows;", desktop)
        self.assertIn("X-NT-Plasma-Origin=windows", desktop)
        self.assertIn("Icon=/mnt/c/Windows/System32/notepad.exe", desktop)
        self.assertNotIn("Exec=/opt/nt-plasma/bin/launch-windows-app notepad.exe", desktop)

    def test_invalid_records_are_skipped(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            catalog = root / "catalog.json"
            catalog.write_text(json.dumps([{"id": "missing-name"}, {"name": "missing-id"}]), encoding="utf-8")

            self.assertEqual(generate_entries(catalog, root / "applications"), 0)

    def test_module_cli_generates_entries(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            catalog = root / "catalog.json"
            catalog.write_text(json.dumps([{"id": "windows:test", "name": "Test"}]), encoding="utf-8")
            output = root / "applications"
            result = subprocess.run(
                ["python3", "-m", "integration.generate_kde_entries", str(catalog), str(output)],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.stdout.strip(), "1")


if __name__ == "__main__":
    unittest.main()