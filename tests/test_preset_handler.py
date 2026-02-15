#!/usr/bin/env python3
"""
Unit tests for foxblat.preset_handler

Tests preset save/load, linked process/vehicle, and plugin settings.
Uses mocked connection_manager to avoid real device communication.
"""

import unittest
import sys
import os
import tempfile
import shutil
import yaml
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("FOXBLAT_FLATPAK_EDITION", "false")

from foxblat.preset_handler import MozaPresetHandler, MozaDevicePresetSettings


class TestMozaPresetHandlerSetup(unittest.TestCase):
    """Test basic preset handler setup."""

    def test_construction(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        self.assertIsNotNone(handler)

    def test_set_path(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        handler.set_path("/tmp/test-presets")
        self.assertEqual(handler._path, "/tmp/test-presets")

    def test_set_path_expands_user(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        handler.set_path("~/presets")
        self.assertNotIn("~", handler._path)

    def test_set_name_adds_yml(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        handler.set_name("my-preset")
        self.assertEqual(handler._name, "my-preset.yml")

    def test_set_name_no_double_yml(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        handler.set_name("my-preset.yml")
        self.assertEqual(handler._name, "my-preset.yml")


class TestMozaPresetHandlerSettings(unittest.TestCase):
    """Test settings management."""

    def test_append_setting(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        handler.append_setting("base-max-angle")
        self.assertIn("base", handler._settings)
        self.assertIn("max-angle", handler._settings["base"])

    def test_append_multiple_settings(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        handler.append_setting("base-max-angle")
        handler.append_setting("base-ffb-strength")
        self.assertEqual(len(handler._settings["base"]), 2)

    def test_add_device_settings(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        handler.add_device_settings("pedals")
        self.assertIn("pedals", handler._settings)
        self.assertTrue(len(handler._settings["pedals"]) > 0)

    def test_add_base_includes_main(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        handler.add_device_settings("base")
        self.assertIn("base", handler._settings)
        self.assertIn("main", handler._settings)

    def test_add_unknown_device_no_error(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        handler.add_device_settings("nonexistent")
        self.assertNotIn("nonexistent", handler._settings)

    def test_reset_settings(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        handler.add_device_settings("pedals")
        handler.reset_settings()
        self.assertEqual(len(handler._settings), 0)


class TestMozaPresetHandlerHPatternStalks(unittest.TestCase):
    """Test H-pattern and stalks settings."""

    def test_set_get_hpattern(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        settings = {"gear1": 100, "gear2": 200}
        handler.set_hpattern_settings(settings)
        self.assertEqual(handler.get_hpattern_settings(), settings)

    def test_set_get_stalks(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        settings = {"mode": "compat"}
        handler.set_stalks_settings(settings)
        self.assertEqual(handler.get_stalks_settings(), settings)


class TestMozaPresetHandlerPluginSettings(unittest.TestCase):
    """Test plugin settings management."""

    def test_set_plugin_settings(self):
        cm = MagicMock()
        handler = MozaPresetHandler(cm)
        settings = {"gx-100": {"sensitivity": 80}}
        handler.set_plugin_settings(settings)
        self.assertEqual(handler._plugin_settings, settings)


class TestMozaPresetHandlerFileOps(unittest.TestCase):
    """Test file-based preset operations."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cm = MagicMock()
        self.handler = MozaPresetHandler(self.cm)
        self.handler.set_path(self.tmpdir)
        self.handler.set_name("test-preset")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write_preset(self, data):
        filepath = os.path.join(self.tmpdir, "test-preset.yml")
        with open(filepath, "w") as f:
            yaml.safe_dump(data, f)

    def test_get_preset_data_no_file(self):
        result = self.handler._get_preset_data()
        self.assertIsNone(result)

    def test_get_preset_data_existing(self):
        self._write_preset({"key": "value"})
        result = self.handler._get_preset_data()
        self.assertEqual(result, {"key": "value"})

    def test_set_preset_data_creates_file(self):
        self.handler._set_preset_data({"saved": True})
        filepath = os.path.join(self.tmpdir, "test-preset.yml")
        self.assertTrue(os.path.isfile(filepath))

    def test_set_preset_data_creates_directory(self):
        nested_path = os.path.join(self.tmpdir, "nested", "presets")
        self.handler.set_path(nested_path)
        self.handler._set_preset_data({"data": 1})
        self.assertTrue(os.path.isdir(nested_path))

    def test_linked_process_roundtrip(self):
        self._write_preset({})
        self.handler.set_linked_process("game.exe")
        result = self.handler.get_linked_process()
        self.assertEqual(result, "game.exe")

    def test_get_linked_process_no_file(self):
        result = self.handler.get_linked_process()
        self.assertEqual(result, "")

    def test_get_linked_process_no_key(self):
        self._write_preset({"other": "data"})
        result = self.handler.get_linked_process()
        self.assertEqual(result, "")

    def test_linked_vehicle_roundtrip(self):
        self._write_preset({})
        self.handler.set_linked_vehicle("Ferrari 488")
        result = self.handler.get_linked_vehicle()
        self.assertEqual(result, "Ferrari 488")

    def test_get_linked_vehicle_no_file(self):
        result = self.handler.get_linked_vehicle()
        self.assertEqual(result, "")

    def test_get_linked_vehicle_no_key(self):
        self._write_preset({"other": "data"})
        result = self.handler.get_linked_vehicle()
        self.assertEqual(result, "")

    def test_is_default_false_when_missing(self):
        self.assertFalse(self.handler.is_default())

    def test_is_default_false_when_not_set(self):
        self._write_preset({"other": "data"})
        self.assertFalse(self.handler.is_default())

    def test_set_and_check_default(self):
        self._write_preset({})
        self.handler.set_default(True)
        self.assertTrue(self.handler.is_default())

    def test_unset_default(self):
        self._write_preset({"is-default": True})
        self.handler.set_default(False)
        self.assertFalse(self.handler.is_default())

    def test_copy_preset(self):
        self._write_preset({"key": "value", "base": {"angle": 900}})
        self.handler.copy_preset("copy-preset")
        copy_path = os.path.join(self.tmpdir, "copy-preset.yml")
        self.assertTrue(os.path.isfile(copy_path))
        with open(copy_path) as f:
            data = yaml.safe_load(f)
        self.assertEqual(data["key"], "value")

    def test_save_imported_preset(self):
        preset_data = {
            "FoxblatPresetVersion": "1",
            "base": {"max-angle": 900},
        }
        self.handler.save_imported_preset(preset_data)
        filepath = os.path.join(self.tmpdir, "test-preset.yml")
        self.assertTrue(os.path.isfile(filepath))
        with open(filepath) as f:
            data = yaml.safe_load(f)
        self.assertEqual(data["base"]["max-angle"], 900)

    def test_save_imported_preset_no_path(self):
        handler = MozaPresetHandler(self.cm)
        # No path/name set — should not crash
        handler.save_imported_preset({"data": 1})

    def test_get_plugin_settings_from_file(self):
        self._write_preset({
            "base": {"angle": 900},
            "plugin-gx100": {"sensitivity": 80},
            "plugin-custom": {"mode": "fast"},
        })
        result = self.handler.get_plugin_settings()
        self.assertEqual(result["gx100"]["sensitivity"], 80)
        self.assertEqual(result["custom"]["mode"], "fast")

    def test_get_plugin_settings_no_plugins(self):
        self._write_preset({"base": {"angle": 900}})
        result = self.handler.get_plugin_settings()
        self.assertEqual(result, {})

    def test_get_plugin_settings_no_file(self):
        result = self.handler.get_plugin_settings()
        self.assertEqual(result, {})


class TestMozaPresetHandlerSavePreset(unittest.TestCase):
    """Test _save_preset with mocked connection manager."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cm = MagicMock()
        self.handler = MozaPresetHandler(self.cm)
        self.handler.set_path(self.tmpdir)
        self.handler.set_name("save-test")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_save_preset_no_path(self):
        handler = MozaPresetHandler(self.cm)
        # No path set — should not crash
        handler._save_preset()

    def test_save_creates_version_key(self):
        self.cm.get_setting.return_value = 50
        self.handler.add_device_settings("pedals")
        self.handler._save_preset()

        filepath = os.path.join(self.tmpdir, "save-test.yml")
        with open(filepath) as f:
            data = yaml.safe_load(f)
        self.assertEqual(data["FoxblatPresetVersion"], "1")

    def test_save_reads_settings_from_cm(self):
        self.cm.get_setting.return_value = 42
        self.handler.append_setting("base-max-angle")
        self.handler._save_preset()

        filepath = os.path.join(self.tmpdir, "save-test.yml")
        with open(filepath) as f:
            data = yaml.safe_load(f)
        self.assertEqual(data["base"]["max-angle"], 42)

    def test_save_includes_plugin_settings(self):
        self.cm.get_setting.return_value = 50
        self.handler.set_plugin_settings({"my-plugin": {"volume": 80}})
        self.handler._save_preset()

        filepath = os.path.join(self.tmpdir, "save-test.yml")
        with open(filepath) as f:
            data = yaml.safe_load(f)
        self.assertEqual(data["plugin-my-plugin"]["volume"], 80)

    def test_save_includes_hpattern(self):
        self.cm.get_setting.return_value = 50
        self.handler.add_device_settings("hpattern")
        self.handler.set_hpattern_settings({"gear1": 100})
        self.handler._save_preset()

        filepath = os.path.join(self.tmpdir, "save-test.yml")
        with open(filepath) as f:
            data = yaml.safe_load(f)
        self.assertEqual(data["hpattern"]["gear1"], 100)

    def test_save_skips_none_values(self):
        self.cm.get_setting.return_value = None
        self.handler.append_setting("base-max-angle")
        self.handler._save_preset()

        filepath = os.path.join(self.tmpdir, "save-test.yml")
        with open(filepath) as f:
            data = yaml.safe_load(f)
        self.assertNotIn("max-angle", data.get("base", {}))


class TestMozaPresetHandlerLoadPreset(unittest.TestCase):
    """Test _load_preset with mocked connection manager."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cm = MagicMock()
        self.handler = MozaPresetHandler(self.cm)
        self.handler.set_path(self.tmpdir)
        self.handler.set_name("load-test")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write_preset(self, data):
        filepath = os.path.join(self.tmpdir, "load-test.yml")
        with open(filepath, "w") as f:
            yaml.safe_dump(data, f)

    def test_load_no_path(self):
        handler = MozaPresetHandler(self.cm)
        # Should not crash
        handler._load_preset(None, None)

    def test_load_no_file(self):
        # File doesn't exist — should not crash
        self.handler._load_preset(None, None)

    def test_load_applies_settings(self):
        self._write_preset({
            "base": {"max-angle": 450, "ffb-strength": 80},
        })
        self.cm.get_setting.return_value = 0
        self.handler._load_preset(None, None)

        # set_setting should be called for each loaded setting
        calls = [str(c) for c in self.cm.set_setting.call_args_list]
        self.assertTrue(any("max-angle" in c for c in calls))

    def test_load_skips_none_values(self):
        self._write_preset({
            "base": {"max-angle": None},
        })
        self.handler._load_preset(None, None)
        self.cm.set_setting.assert_not_called()

    def test_load_skips_negative_one_values(self):
        self._write_preset({
            "base": {"max-angle": -1},
        })
        self.handler._load_preset(None, None)
        self.cm.set_setting.assert_not_called()

    def test_load_hpattern(self):
        hpattern_mock = MagicMock()
        self._write_preset({
            "hpattern": {"gear1": 100},
        })
        self.handler._load_preset(hpattern_mock, None)
        hpattern_mock.set_settings.assert_called_once_with({"gear1": 100})

    def test_load_stalks(self):
        stalks_mock = MagicMock()
        self._write_preset({
            "stalks": {"mode": "compat"},
        })
        self.handler._load_preset(None, stalks_mock)
        stalks_mock.set_settings.assert_called_once_with({"mode": "compat"})

    def test_load_skips_unknown_devices(self):
        self._write_preset({
            "unknown-device": {"setting": 42},
            "FoxblatPresetVersion": "1",
        })
        self.handler._load_preset(None, None)
        # Should not crash, set_setting should not be called for unknown devices
        self.cm.set_setting.assert_not_called()

    def test_load_indicator_mode_rename(self):
        """Test backward compat: indicator-mode -> rpm-indicator-mode."""
        self._write_preset({
            "dash": {"indicator-mode": 2},
        })
        self.cm.get_setting.return_value = 0
        self.handler._load_preset(None, None)
        calls = [str(c) for c in self.cm.set_setting.call_args_list]
        self.assertTrue(any("rpm-indicator-mode" in c for c in calls))


class TestMozaDevicePresetSettings(unittest.TestCase):
    """Test the MozaDevicePresetSettings constant."""

    def test_has_expected_devices(self):
        expected = ["main", "base", "dash", "dash-colors", "wheel",
                    "wheel-colors", "pedals", "sequential", "handbrake",
                    "hpattern", "stalks"]
        for device in expected:
            self.assertIn(device, MozaDevicePresetSettings, f"Missing device: {device}")

    def test_all_settings_are_lists(self):
        for device, settings in MozaDevicePresetSettings.items():
            self.assertIsInstance(settings, list, f"{device} settings should be a list")

    def test_base_has_ffb_settings(self):
        base_settings = MozaDevicePresetSettings["base"]
        self.assertIn("base-ffb-strength", base_settings)
        self.assertIn("base-max-angle", base_settings)


if __name__ == "__main__":
    unittest.main(verbosity=2)
