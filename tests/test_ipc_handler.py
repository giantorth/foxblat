#!/usr/bin/env python3
"""
Unit tests for foxblat.ipc_handler

Tests IPC command processing, validation, and response formatting.
Uses mocked connection_manager and settings_handler.
"""

import unittest
import sys
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("FOXBLAT_FLATPAK_EDITION", "false")

from foxblat.ipc_handler import IpcHandler


class TestIpcHandlerInit(unittest.TestCase):
    """Test IPC handler initialization."""

    def test_construction(self):
        cm = MagicMock()
        settings = MagicMock()
        handler = IpcHandler(cm, settings)
        self.assertIsNotNone(handler)

    def test_custom_port(self):
        cm = MagicMock()
        settings = MagicMock()
        handler = IpcHandler(cm, settings, tcp_port=9999)
        self.assertEqual(handler._tcp_port, 9999)

    def test_events_registered(self):
        cm = MagicMock()
        settings = MagicMock()
        handler = IpcHandler(cm, settings)
        events = handler.list_events()
        self.assertIn("preset-loaded", events)


class TestIpcProcessCommand(unittest.TestCase):
    """Test _process_command routing and validation."""

    def setUp(self):
        self.cm = MagicMock()
        self.settings = MagicMock()
        self.handler = IpcHandler(self.cm, self.settings)

    def test_missing_command_field(self):
        result = self.handler._process_command({})
        self.assertEqual(result["status"], "error")
        self.assertIn("Missing", result["message"])

    def test_unknown_command(self):
        result = self.handler._process_command({"command": "fly_to_moon"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Unknown", result["message"])

    def test_ping(self):
        result = self.handler._process_command({"command": "ping"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["message"], "pong")


class TestIpcSetAngle(unittest.TestCase):
    """Test set_angle command."""

    def setUp(self):
        self.cm = MagicMock()
        self.settings = MagicMock()
        self.handler = IpcHandler(self.cm, self.settings)

    def test_valid_angle(self):
        result = self.handler._process_command({"command": "set_angle", "value": 900})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["value"], 900)
        # Should call set_setting with angle/2
        self.cm.set_setting.assert_any_call(450, "base-limit")
        self.cm.set_setting.assert_any_call(450, "base-max-angle")

    def test_missing_value(self):
        result = self.handler._process_command({"command": "set_angle"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Missing", result["message"])

    def test_angle_too_low(self):
        result = self.handler._process_command({"command": "set_angle", "value": 50})
        self.assertEqual(result["status"], "error")
        self.assertIn("90", result["message"])

    def test_angle_too_high(self):
        result = self.handler._process_command({"command": "set_angle", "value": 3000})
        self.assertEqual(result["status"], "error")
        self.assertIn("2700", result["message"])

    def test_angle_min_boundary(self):
        result = self.handler._process_command({"command": "set_angle", "value": 90})
        self.assertEqual(result["status"], "ok")

    def test_angle_max_boundary(self):
        result = self.handler._process_command({"command": "set_angle", "value": 2700})
        self.assertEqual(result["status"], "ok")

    def test_invalid_value_type(self):
        result = self.handler._process_command({"command": "set_angle", "value": "abc"})
        self.assertEqual(result["status"], "error")

    def test_string_numeric_value(self):
        result = self.handler._process_command({"command": "set_angle", "value": "900"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["value"], 900)


class TestIpcGetAngle(unittest.TestCase):
    """Test get_angle command."""

    def setUp(self):
        self.cm = MagicMock()
        self.settings = MagicMock()
        self.handler = IpcHandler(self.cm, self.settings)

    def test_get_angle_success(self):
        self.cm.get_setting.return_value = 450
        result = self.handler._process_command({"command": "get_angle"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["value"], 900)  # 450 * 2

    def test_get_angle_not_connected(self):
        self.cm.get_setting.return_value = None
        result = self.handler._process_command({"command": "get_angle"})
        self.assertEqual(result["status"], "error")
        self.assertIn("not connected", result["message"].lower())


class TestIpcGetStatus(unittest.TestCase):
    """Test get_status command."""

    def setUp(self):
        self.cm = MagicMock()
        self.settings = MagicMock()
        self.handler = IpcHandler(self.cm, self.settings)

    def test_connected(self):
        self.cm.get_setting.return_value = 450
        result = self.handler._process_command({"command": "get_status"})
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["base_connected"])

    def test_disconnected(self):
        self.cm.get_setting.return_value = None
        result = self.handler._process_command({"command": "get_status"})
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["base_connected"])


class TestIpcListPresets(unittest.TestCase):
    """Test list_presets command."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cm = MagicMock()
        self.settings = MagicMock()
        self.settings.get_path.return_value = self.tmpdir
        self.handler = IpcHandler(self.cm, self.settings)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_no_presets_dir(self):
        result = self.handler._process_command({"command": "list_presets"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["presets"], [])

    def test_with_presets(self):
        presets_dir = os.path.join(self.tmpdir, "presets")
        os.makedirs(presets_dir)
        for name in ["GT3.yml", "Rally.yml", "Drift.yml"]:
            with open(os.path.join(presets_dir, name), "w") as f:
                f.write("")

        result = self.handler._process_command({"command": "list_presets"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["count"], 3)
        self.assertIn("GT3", result["presets"])
        self.assertIn("Rally", result["presets"])
        self.assertIn("Drift", result["presets"])

    def test_ignores_non_yml_files(self):
        presets_dir = os.path.join(self.tmpdir, "presets")
        os.makedirs(presets_dir)
        with open(os.path.join(presets_dir, "GT3.yml"), "w") as f:
            f.write("")
        with open(os.path.join(presets_dir, "readme.txt"), "w") as f:
            f.write("")

        result = self.handler._process_command({"command": "list_presets"})
        self.assertEqual(result["count"], 1)
        self.assertIn("GT3", result["presets"])

    def test_sorted_output(self):
        presets_dir = os.path.join(self.tmpdir, "presets")
        os.makedirs(presets_dir)
        for name in ["Zebra.yml", "Alpha.yml", "Mid.yml"]:
            with open(os.path.join(presets_dir, name), "w") as f:
                f.write("")

        result = self.handler._process_command({"command": "list_presets"})
        self.assertEqual(result["presets"], ["Alpha", "Mid", "Zebra"])


class TestIpcLoadPreset(unittest.TestCase):
    """Test load_preset command."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cm = MagicMock()
        self.settings = MagicMock()
        self.settings.get_path.return_value = self.tmpdir
        self.handler = IpcHandler(self.cm, self.settings)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_missing_name(self):
        result = self.handler._process_command({"command": "load_preset"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Missing", result["message"])

    def test_preset_not_found(self):
        presets_dir = os.path.join(self.tmpdir, "presets")
        os.makedirs(presets_dir)
        result = self.handler._process_command({"command": "load_preset", "name": "nonexistent"})
        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["message"])

    @patch("foxblat.preset_handler.MozaPresetHandler")
    def test_load_success(self, MockPresetHandler):
        presets_dir = os.path.join(self.tmpdir, "presets")
        os.makedirs(presets_dir)
        with open(os.path.join(presets_dir, "GT3.yml"), "w") as f:
            f.write("base:\n  max-angle: 900\n")

        events = []
        self.handler.subscribe("preset-loaded", lambda name: events.append(name))

        result = self.handler._process_command({"command": "load_preset", "name": "GT3"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["preset"], "GT3")
        MockPresetHandler.assert_called_once()
        self.assertIn("GT3", events)

    @patch("foxblat.preset_handler.MozaPresetHandler")
    def test_load_strips_yml_extension(self, MockPresetHandler):
        presets_dir = os.path.join(self.tmpdir, "presets")
        os.makedirs(presets_dir)
        with open(os.path.join(presets_dir, "GT3.yml"), "w") as f:
            f.write("")

        result = self.handler._process_command({"command": "load_preset", "name": "GT3.yml"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["preset"], "GT3")


class TestIpcHandlerLifecycle(unittest.TestCase):
    """Test start/stop lifecycle."""

    def test_stop_clears_running(self):
        cm = MagicMock()
        settings = MagicMock()
        handler = IpcHandler(cm, settings)
        handler._running.set()
        handler.stop()
        self.assertFalse(handler._running.is_set())

    def test_start_already_running(self):
        cm = MagicMock()
        settings = MagicMock()
        handler = IpcHandler(cm, settings)
        handler._running.set()
        result = handler.start()
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
