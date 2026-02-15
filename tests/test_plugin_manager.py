#!/usr/bin/env python3
"""
Unit tests for foxblat.plugin_manager

Tests PluginMatcher, LoadedPlugin, and PluginManager classes.
Uses mocks for evdev devices, HidHandler, and SettingsHandler.
"""

import unittest
import sys
import os
import json
import tempfile
import shutil
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from foxblat.plugin_manager import PluginMatcher, LoadedPlugin, PluginManager
from foxblat.plugin_base import PluginPanel, PluginContext, PluginDeviceInfo


def _make_mock_device(name="Test Device", vendor=0x04b0, product=0x5750, path="/dev/input/event0"):
    """Create a mock evdev InputDevice."""
    device = MagicMock()
    device.name = name
    device.path = path
    device.info = MagicMock()
    device.info.vendor = vendor
    device.info.product = product
    return device


class TestPluginMatcher(unittest.TestCase):
    """Test cases for the PluginMatcher class."""

    def test_vid_pid_hex_string_match(self):
        metadata = {"devices": [{"vendor_id": "0x04b0", "product_id": "0x5750"}]}
        matcher = PluginMatcher("test", metadata)
        device = _make_mock_device(vendor=0x04b0, product=0x5750)
        self.assertTrue(matcher.matches(device))

    def test_vid_pid_int_match(self):
        metadata = {"devices": [{"vendor_id": 1200, "product_id": 22352}]}
        matcher = PluginMatcher("test", metadata)
        device = _make_mock_device(vendor=1200, product=22352)
        self.assertTrue(matcher.matches(device))

    def test_vid_pid_no_match(self):
        metadata = {"devices": [{"vendor_id": "0x04b0", "product_id": "0x5750"}]}
        matcher = PluginMatcher("test", metadata)
        device = _make_mock_device(vendor=0x1234, product=0x5678)
        self.assertFalse(matcher.matches(device))

    def test_name_pattern_match(self):
        metadata = {"devices": [{"name_pattern": "GX-100.*"}]}
        matcher = PluginMatcher("test", metadata)
        device = _make_mock_device(name="GX-100 Shifter v2")
        self.assertTrue(matcher.matches(device))

    def test_name_pattern_case_insensitive(self):
        metadata = {"devices": [{"name_pattern": "gx-100"}]}
        matcher = PluginMatcher("test", metadata)
        device = _make_mock_device(name="GX-100 Shifter")
        self.assertTrue(matcher.matches(device))

    def test_name_pattern_no_match(self):
        metadata = {"devices": [{"name_pattern": "SomeOtherDevice"}]}
        matcher = PluginMatcher("test", metadata)
        device = _make_mock_device(name="GX-100 Shifter")
        self.assertFalse(matcher.matches(device))

    def test_multiple_rules_or_logic(self):
        metadata = {"devices": [
            {"vendor_id": "0xAAAA", "product_id": "0xBBBB"},
            {"name_pattern": "GX-100"},
        ]}
        matcher = PluginMatcher("test", metadata)

        # Matches second rule (name) but not first (VID/PID)
        device = _make_mock_device(name="GX-100 Shifter", vendor=0x0000, product=0x0000)
        self.assertTrue(matcher.matches(device))

    def test_empty_devices_list(self):
        metadata = {"devices": []}
        matcher = PluginMatcher("test", metadata)
        device = _make_mock_device()
        self.assertFalse(matcher.matches(device))

    def test_no_devices_key(self):
        metadata = {}
        matcher = PluginMatcher("test", metadata)
        device = _make_mock_device()
        self.assertFalse(matcher.matches(device))


class TestLoadedPlugin(unittest.TestCase):
    """Test cases for the LoadedPlugin data class."""

    def test_construction(self):
        lp = LoadedPlugin(
            name="test-plugin",
            metadata={"name": "Test"},
            module=MagicMock(),
            panel_class=MagicMock(),
            matcher=MagicMock(),
            path="/plugins/test"
        )
        self.assertEqual(lp.name, "test-plugin")
        self.assertIsNone(lp.panel_instance)
        self.assertEqual(lp.connected_devices, [])


class TestPluginManagerLoadPlugin(unittest.TestCase):
    """Test plugin loading with temporary directories."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.plugins_dir = os.path.join(self.tmpdir, "plugins")
        os.makedirs(self.plugins_dir)

        self.hid_handler = MagicMock()
        self.settings_handler = MagicMock()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _make_manager(self):
        manager = PluginManager(self.tmpdir, self.hid_handler, self.settings_handler)
        return manager

    def _create_plugin_dir(self, name, metadata=None, init_content=None, create_init=True):
        """Create a plugin directory with optional files."""
        plugin_dir = os.path.join(self.plugins_dir, name)
        os.makedirs(plugin_dir, exist_ok=True)

        if metadata is not None:
            with open(os.path.join(plugin_dir, "plugin.json"), "w") as f:
                json.dump(metadata, f)

        if create_init:
            init_path = os.path.join(plugin_dir, "__init__.py")
            content = init_content or ""
            with open(init_path, "w") as f:
                f.write(content)

        return plugin_dir

    def test_load_plugin_missing_json(self):
        manager = self._make_manager()
        plugin_dir = self._create_plugin_dir("broken", create_init=True)
        # No plugin.json
        result = manager._load_plugin("broken", plugin_dir)
        self.assertFalse(result)

    def test_load_plugin_missing_init(self):
        manager = self._make_manager()
        plugin_dir = self._create_plugin_dir("broken", metadata={"name": "B", "panel_class": "X", "devices": []}, create_init=False)
        result = manager._load_plugin("broken", plugin_dir)
        self.assertFalse(result)

    def test_load_plugin_invalid_json(self):
        manager = self._make_manager()
        plugin_dir = os.path.join(self.plugins_dir, "badjson")
        os.makedirs(plugin_dir)
        with open(os.path.join(plugin_dir, "plugin.json"), "w") as f:
            f.write("{invalid json")
        with open(os.path.join(plugin_dir, "__init__.py"), "w") as f:
            f.write("")
        result = manager._load_plugin("badjson", plugin_dir)
        self.assertFalse(result)

    def test_load_plugin_missing_required_fields(self):
        manager = self._make_manager()
        # Missing "devices" field
        plugin_dir = self._create_plugin_dir("incomplete",
            metadata={"name": "Test", "panel_class": "TestPanel"})
        result = manager._load_plugin("incomplete", plugin_dir)
        self.assertFalse(result)

    def test_load_plugin_missing_panel_class_field(self):
        manager = self._make_manager()
        plugin_dir = self._create_plugin_dir("incomplete2",
            metadata={"name": "Test", "devices": []})
        result = manager._load_plugin("incomplete2", plugin_dir)
        self.assertFalse(result)

    def test_load_plugin_class_not_found_in_module(self):
        manager = self._make_manager()
        plugin_dir = self._create_plugin_dir("noclass",
            metadata={"name": "Test", "panel_class": "MissingClass", "devices": []},
            init_content="# empty module\n")
        result = manager._load_plugin("noclass", plugin_dir)
        self.assertFalse(result)

    @patch("foxblat.plugin_base.SettingsPanel.__init__", lambda self, *a, **kw: None)
    def test_load_plugin_class_not_subclass(self):
        manager = self._make_manager()
        init_content = "class NotAPlugin:\n    pass\n"
        plugin_dir = self._create_plugin_dir("wrongclass",
            metadata={"name": "Test", "panel_class": "NotAPlugin", "devices": []},
            init_content=init_content)
        result = manager._load_plugin("wrongclass", plugin_dir)
        self.assertFalse(result)

    @patch("foxblat.plugin_base.SettingsPanel.__init__", lambda self, *a, **kw: None)
    def test_load_valid_plugin(self):
        manager = self._make_manager()
        init_content = (
            "from foxblat.plugin_base import PluginPanel\n"
            "class TestPanel(PluginPanel):\n"
            "    def prepare_ui(self):\n"
            "        pass\n"
        )
        plugin_dir = self._create_plugin_dir("valid",
            metadata={
                "name": "Valid Plugin",
                "panel_class": "TestPanel",
                "devices": [{"vendor_id": "0x1234", "product_id": "0x5678"}]
            },
            init_content=init_content)
        result = manager._load_plugin("valid", plugin_dir)
        self.assertTrue(result)
        self.assertIn("valid", manager._plugins)
        self.assertEqual(manager._plugins["valid"].name, "valid")


class TestPluginManagerDiscovery(unittest.TestCase):
    """Test plugin discovery from directory scanning."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.plugins_dir = os.path.join(self.tmpdir, "plugins")
        os.makedirs(self.plugins_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_ensure_plugins_directory_creates_dir(self):
        new_dir = os.path.join(self.tmpdir, "new_config")
        manager = PluginManager(new_dir, MagicMock(), MagicMock())
        manager._ensure_plugins_directory()
        self.assertTrue(os.path.isdir(os.path.join(new_dir, "plugins")))

    def test_discover_empty_directory(self):
        manager = PluginManager(self.tmpdir, MagicMock(), MagicMock())
        manager._discover_plugins()
        self.assertEqual(len(manager._plugins), 0)

    def test_discover_skips_files(self):
        # Create a file (not a directory) in plugins/
        with open(os.path.join(self.plugins_dir, "not-a-plugin.txt"), "w") as f:
            f.write("hello")
        manager = PluginManager(self.tmpdir, MagicMock(), MagicMock())
        manager._discover_plugins()
        self.assertEqual(len(manager._plugins), 0)


class TestPluginManagerDeviceHandling(unittest.TestCase):
    """Test device connect/disconnect handling."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.manager = PluginManager(self.tmpdir, MagicMock(), MagicMock())
        self.manager._button_callback = MagicMock()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _add_loaded_plugin(self, name="test", vid=0x04b0, pid=0x5750):
        """Manually register a loaded plugin with a matcher."""
        matcher = PluginMatcher(name, {"devices": [{"vendor_id": vid, "product_id": pid}]})
        plugin = LoadedPlugin(
            name=name,
            metadata={"name": name, "panel_class": "FakePanel", "panel_title": name, "devices": []},
            module=MagicMock(),
            panel_class=MagicMock(),
            matcher=matcher,
            path="/fake/path"
        )
        self.manager._plugins[name] = plugin
        return plugin

    def test_handle_device_connected_matching(self):
        plugin = self._add_loaded_plugin()
        device = _make_mock_device(vendor=0x04b0, product=0x5750)

        with patch.object(self.manager, "_instantiate_plugin_panel"):
            self.manager._handle_device_connected(device)

        self.assertEqual(len(plugin.connected_devices), 1)
        self.assertEqual(plugin.connected_devices[0].name, "Test Device")

    def test_handle_device_connected_no_match(self):
        plugin = self._add_loaded_plugin()
        device = _make_mock_device(vendor=0xFFFF, product=0xFFFF)

        self.manager._handle_device_connected(device)
        self.assertEqual(len(plugin.connected_devices), 0)

    def test_handle_device_disconnected(self):
        plugin = self._add_loaded_plugin()
        device_info = PluginDeviceInfo("Test", 0x04b0, 0x5750, "/dev/input/event0")
        plugin.connected_devices.append(device_info)
        plugin.panel_instance = MagicMock()

        self.manager._handle_device_disconnected("/dev/input/event0")

        self.assertEqual(len(plugin.connected_devices), 0)
        plugin.panel_instance.on_device_disconnected.assert_called_once_with(device_info)

    def test_handle_device_disconnected_hides_panel_when_no_devices(self):
        plugin = self._add_loaded_plugin()
        device_info = PluginDeviceInfo("Test", 0x04b0, 0x5750, "/dev/input/event0")
        plugin.connected_devices.append(device_info)
        plugin.panel_instance = MagicMock()

        self.manager._handle_device_disconnected("/dev/input/event0")

        plugin.panel_instance.active.assert_called_once_with(-1)

    def test_handle_device_disconnected_unknown_path(self):
        plugin = self._add_loaded_plugin()
        plugin.panel_instance = MagicMock()
        # Should not raise or call anything
        self.manager._handle_device_disconnected("/dev/input/event99")
        plugin.panel_instance.on_device_disconnected.assert_not_called()


class TestPluginManagerPresets(unittest.TestCase):
    """Test preset integration in PluginManager."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.manager = PluginManager(self.tmpdir, MagicMock(), MagicMock())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _add_active_plugin(self, name="test", preset_name="test-device"):
        plugin = LoadedPlugin(
            name=name,
            metadata={"name": name, "panel_class": "FakePanel", "devices": []},
            module=MagicMock(),
            panel_class=MagicMock(),
            matcher=MagicMock(),
            path="/fake"
        )
        panel = MagicMock()
        panel.preset_device_name = preset_name
        panel.get_preset_settings.return_value = {"sensitivity": 80}
        plugin.panel_instance = panel
        plugin.connected_devices = [MagicMock()]
        self.manager._plugins[name] = plugin
        return plugin, panel

    def test_get_active_plugins(self):
        self._add_active_plugin("p1", "device-1")
        self._add_active_plugin("p2", "device-2")

        result = self.manager.get_active_plugins()
        self.assertEqual(len(result), 2)
        self.assertIn("device-1", result)
        self.assertIn("device-2", result)

    def test_get_active_plugins_excludes_no_devices(self):
        plugin, _ = self._add_active_plugin()
        plugin.connected_devices = []  # No devices

        result = self.manager.get_active_plugins()
        self.assertEqual(len(result), 0)

    def test_get_plugin_preset_settings(self):
        self._add_active_plugin("p1", "my-device")
        result = self.manager.get_plugin_preset_settings("my-device")
        self.assertEqual(result, {"sensitivity": 80})

    def test_get_plugin_preset_settings_unknown_device(self):
        result = self.manager.get_plugin_preset_settings("nonexistent")
        self.assertEqual(result, {})

    def test_apply_plugin_preset_settings(self):
        _, panel = self._add_active_plugin("p1", "my-device")
        settings = {"sensitivity": 100}
        self.manager.apply_plugin_preset_settings("my-device", settings)
        panel.on_preset_loaded.assert_called_once_with(settings)

    def test_apply_plugin_preset_settings_unknown_device(self):
        # Should not raise
        self.manager.apply_plugin_preset_settings("nonexistent", {"key": "value"})

    def test_has_active_plugins_true(self):
        self._add_active_plugin()
        self.assertTrue(self.manager.has_active_plugins())

    def test_has_active_plugins_false(self):
        self.assertFalse(self.manager.has_active_plugins())

    def test_stop_calls_shutdown(self):
        plugin, panel = self._add_active_plugin()
        self.manager._running.set()
        self.manager.stop()
        panel.shutdown.assert_called_once()


class TestPluginManagerEvents(unittest.TestCase):
    """Test PluginManager event registration."""

    def test_events_registered(self):
        tmpdir = tempfile.mkdtemp()
        try:
            manager = PluginManager(tmpdir, MagicMock(), MagicMock())
            events = manager.list_events()
            self.assertIn("plugin-panel-available", events)
            self.assertIn("plugin-panel-unavailable", events)
            self.assertIn("plugin-load-error", events)
        finally:
            shutil.rmtree(tmpdir)

    def test_subscribe_to_load_error(self):
        tmpdir = tempfile.mkdtemp()
        try:
            manager = PluginManager(tmpdir, MagicMock(), MagicMock())
            errors = []
            manager.subscribe("plugin-load-error", lambda name, msg: errors.append((name, msg)))

            # Trigger an error by loading from nonexistent directory
            manager._load_plugin("fake", os.path.join(tmpdir, "plugins", "fake"))
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0][0], "fake")
        finally:
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    unittest.main(verbosity=2)
