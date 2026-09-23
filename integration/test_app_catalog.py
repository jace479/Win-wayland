import unittest

from integration.app_catalog import ApplicationCatalog, ApplicationEntry
from integration.bridge_protocol import ProtocolError


class ApplicationCatalogTests(unittest.TestCase):
    def test_catalog_hides_executable_paths_from_desktop(self):
        catalog = ApplicationCatalog(
            (ApplicationEntry("notepad", "Notepad", "notepad.exe", category="Utilities"),)
        )

        self.assertEqual(
            catalog.list_for_desktop(),
            [
                {
                    "id": "notepad",
                    "name": "Notepad",
                    "category": "Utilities",
                    "origin": "linux",
                    "arguments": [],
                }
            ],
        )

    def test_catalog_is_sorted_for_start_menu_display(self):
        catalog = ApplicationCatalog(
            (
                ApplicationEntry("z", "Zed", "zed.exe"),
                ApplicationEntry("a", "Calculator", "calc.exe"),
            )
        )

        self.assertEqual([item["name"] for item in catalog.list_for_desktop()], ["Calculator", "Zed"])

    def test_duplicate_and_unknown_entries_are_rejected(self):
        entry = ApplicationEntry("notepad", "Notepad", "notepad.exe")
        catalog = ApplicationCatalog((entry,))
        with self.assertRaises(ProtocolError):
            catalog.add(entry)
        with self.assertRaises(ProtocolError):
            catalog.resolve("cmd")

    def test_windows_and_linux_entries_share_one_desktop_schema(self):
        catalog = ApplicationCatalog(
            (ApplicationEntry("kate", "Kate", "/usr/bin/kate", origin="linux"),)
        )
        catalog.merge(
            (ApplicationEntry("notepad", "Notepad", "notepad.exe", origin="windows"),)
        )

        self.assertEqual(
            [(item["id"], item["origin"]) for item in catalog.list_for_desktop()],
            [("kate", "linux"), ("notepad", "windows")],
        )


if __name__ == "__main__":
    unittest.main()