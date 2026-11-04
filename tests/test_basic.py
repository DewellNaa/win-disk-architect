import os
import unittest
from windisk.utils.system import format_size, get_fixed_drives, get_largest_free_drive, is_junction_or_reparse
from windisk.core.compact import query_compact_state

class TestWinDisk(unittest.TestCase):
    def test_format_size(self):
        self.assertEqual(format_size(0), "   0.0 KB")
        self.assertEqual(format_size(1024), "   1.0 KB")
        self.assertEqual(format_size(1024 * 1024), "   1.0 MB")
        self.assertEqual(format_size(1024 * 1024 * 1024), "  1.00 GB")
        self.assertEqual(format_size(1024 * 1024 * 1024 * 1024), "  1.00 TB")
        self.assertEqual(format_size(-1), "Unknown")
        self.assertEqual(format_size(None), "Unknown")

    def test_get_fixed_drives(self):
        drives = get_fixed_drives()
        self.assertIsInstance(drives, list)
        self.assertIn("C", drives)

    def test_get_largest_free_drive(self):
        target = get_largest_free_drive(exclude_drives=["C"])
        if target:
            self.assertNotEqual(target, "C")

    def test_compact_state(self):
        is_compact, msg = query_compact_state()
        self.assertIsInstance(is_compact, bool)
        self.assertIsInstance(msg, str)

if __name__ == "__main__":
    unittest.main()
