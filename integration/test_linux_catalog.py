import tempfile
import unittest
from pathlib import Path

from integration.linux_catalog import scan_linux_applications


class LinuxCatalogTests(unittest.TestCase):
    def test_scans_visible_application_and_normalizes_exec(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "kate.desktop").write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Kate\n"
                "Exec=/usr/bin/kate %U\n"
                "Categories=Utility;TextEditor;\n"
                "Icon=kate\n",
                encoding="utf-8",
            )

            entries = scan_linux_applications((root,))

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].application_id, "linux:kate")
        self.assertEqual(entries[0].executable, "/usr/bin/kate")
        self.assertEqual(entries[0].arguments, ())
        self.assertEqual(entries[0].origin, "linux")

    def test_hidden_nodisplay_and_non_application_entries_are_ignored(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for name, flags in {
                "hidden.desktop": "Hidden=true\n",
                "nodisplay.desktop": "NoDisplay=true\n",
                "link.desktop": "Type=Link\nURL=https://example.com\n",
            }.items():
                (root / name).write_text(
                    "[Desktop Entry]\nType=Application\nName=Ignored\n"
                    "Exec=/bin/false\n" + flags,
                    encoding="utf-8",
                )

            self.assertEqual(scan_linux_applications((root,)), ())

    def test_duplicate_desktop_files_use_first_root(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_root, second_root = Path(first), Path(second)
            content = "[Desktop Entry]\nType=Application\nName={name}\nExec=/bin/true\n"
            (first_root / "same.desktop").write_text(content.format(name="First"), encoding="utf-8")
            (second_root / "same.desktop").write_text(content.format(name="Second"), encoding="utf-8")

            entries = scan_linux_applications((first_root, second_root))

        self.assertEqual(entries[0].display_name, "First")


if __name__ == "__main__":
    unittest.main()