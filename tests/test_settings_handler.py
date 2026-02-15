#!/usr/bin/env python3
"""
Unit tests for foxblat.settings_handler

Tests YAML-based persistent settings storage.
"""

import unittest
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from foxblat.settings_handler import SettingsHandler


class TestSettingsHandler(unittest.TestCase):
    """Test cases for SettingsHandler."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = SettingsHandler(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_creates_directory(self):
        new_dir = os.path.join(self.tmpdir, "subdir", "config")
        handler = SettingsHandler(new_dir)
        self.assertTrue(os.path.isdir(new_dir))

    def test_creates_settings_file(self):
        settings_file = os.path.join(self.tmpdir, "settings.yml")
        self.assertTrue(os.path.isfile(settings_file))

    def test_write_and_read_string(self):
        self.handler.write_setting("hello", "greeting")
        self.assertEqual(self.handler.read_setting("greeting"), "hello")

    def test_write_and_read_int(self):
        self.handler.write_setting(42, "answer")
        self.assertEqual(self.handler.read_setting("answer"), 42)

    def test_write_and_read_float(self):
        self.handler.write_setting(3.14, "pi")
        self.assertAlmostEqual(self.handler.read_setting("pi"), 3.14)

    def test_write_and_read_bool(self):
        self.handler.write_setting(True, "flag")
        self.assertTrue(self.handler.read_setting("flag"))

    def test_write_and_read_list(self):
        self.handler.write_setting([1, 2, 3], "numbers")
        self.assertEqual(self.handler.read_setting("numbers"), [1, 2, 3])

    def test_write_and_read_dict(self):
        data = {"key": "value", "nested": {"a": 1}}
        self.handler.write_setting(data, "config")
        self.assertEqual(self.handler.read_setting("config"), data)

    def test_read_nonexistent_setting(self):
        self.assertIsNone(self.handler.read_setting("does-not-exist"))

    def test_overwrite_setting(self):
        self.handler.write_setting(1, "counter")
        self.handler.write_setting(2, "counter")
        self.assertEqual(self.handler.read_setting("counter"), 2)

    def test_multiple_settings(self):
        self.handler.write_setting("a", "setting1")
        self.handler.write_setting("b", "setting2")
        self.handler.write_setting("c", "setting3")
        self.assertEqual(self.handler.read_setting("setting1"), "a")
        self.assertEqual(self.handler.read_setting("setting2"), "b")
        self.assertEqual(self.handler.read_setting("setting3"), "c")

    def test_remove_setting(self):
        self.handler.write_setting("temp", "removable")
        self.assertTrue(self.handler.remove_setting("removable"))
        self.assertIsNone(self.handler.read_setting("removable"))

    def test_remove_nonexistent_setting(self):
        self.assertFalse(self.handler.remove_setting("nope"))

    def test_remove_preserves_other_settings(self):
        self.handler.write_setting("keep", "keeper")
        self.handler.write_setting("drop", "dropper")
        self.handler.remove_setting("dropper")
        self.assertEqual(self.handler.read_setting("keeper"), "keep")

    def test_get_path(self):
        self.assertEqual(self.handler.get_path(), self.tmpdir)

    def test_persistence_across_instances(self):
        self.handler.write_setting("persistent", "data")
        handler2 = SettingsHandler(self.tmpdir)
        self.assertEqual(handler2.read_setting("data"), "persistent")

    def test_write_none_value(self):
        self.handler.write_setting(None, "nullable")
        self.assertIsNone(self.handler.read_setting("nullable"))

    def test_unicode_values(self):
        self.handler.write_setting("日本語テスト", "unicode")
        self.assertEqual(self.handler.read_setting("unicode"), "日本語テスト")

    def test_empty_string_value(self):
        self.handler.write_setting("", "empty")
        self.assertEqual(self.handler.read_setting("empty"), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
