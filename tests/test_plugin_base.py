#!/usr/bin/env python3
"""
Unit tests for foxblat.plugin_base

Tests PluginContext, PluginDeviceInfo, and PluginPanel classes.
PluginPanel depends on GTK via SettingsPanel, so we mock it.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Set env var before importing foxblat modules to avoid KeyError in panels/__init__.py
os.environ.setdefault("FOXBLAT_FLATPAK_EDITION", "false")

from foxblat.plugin_base import PluginContext, PluginDeviceInfo


class TestPluginContext(unittest.TestCase):
    """Test cases for the PluginContext class."""

    def test_construction(self):
        hid = MagicMock()
        settings = MagicMock()
        ctx = PluginContext(hid, settings, "/path/to/plugin", "/path/to/config")

        self.assertIs(ctx.hid_handler, hid)
        self.assertIs(ctx.settings_handler, settings)
        self.assertEqual(ctx.plugin_path, "/path/to/plugin")
        self.assertEqual(ctx.config_path, "/path/to/config")


class TestPluginDeviceInfo(unittest.TestCase):
    """Test cases for the PluginDeviceInfo class."""

    def test_construction(self):
        info = PluginDeviceInfo("My Device", 0x04b0, 0x5750, "/dev/input/event5")

        self.assertEqual(info.name, "My Device")
        self.assertEqual(info.vendor_id, 0x04b0)
        self.assertEqual(info.product_id, 0x5750)
        self.assertEqual(info.path, "/dev/input/event5")

    def test_attributes_mutable(self):
        info = PluginDeviceInfo("dev", 1, 2, "/dev/input/event0")
        info.name = "changed"
        self.assertEqual(info.name, "changed")


class TestPluginPanel(unittest.TestCase):
    """Test cases for PluginPanel with mocked GTK dependencies.

    We patch SettingsPanel.__init__ to avoid GTK initialization.
    """

    @classmethod
    def setUpClass(cls):
        # Patch SettingsPanel.__init__ to be a no-op for all tests in this class
        cls._patcher = patch(
            "foxblat.plugin_base.SettingsPanel.__init__",
            lambda self, *a, **kw: None
        )
        cls._patcher.start()

        # Now import PluginPanel (SettingsPanel.__init__ is already patched)
        from foxblat.plugin_base import PluginPanel
        cls.PluginPanel = PluginPanel

    @classmethod
    def tearDownClass(cls):
        cls._patcher.stop()

    def _make_panel(self, title="Test Panel"):
        """Create a PluginPanel subclass instance with mocked context."""
        settings_handler = MagicMock()
        settings_handler.read_setting.return_value = None
        ctx = PluginContext(
            hid_handler=MagicMock(),
            settings_handler=settings_handler,
            plugin_path="/plugins/test",
            config_path="/config"
        )

        # Create a concrete subclass since PluginPanel is abstract
        class ConcretePanel(self.PluginPanel):
            def prepare_ui(self):
                pass

        panel = ConcretePanel.__new__(ConcretePanel)
        panel._context = ctx
        panel._connected_devices = {}
        return panel

    def test_context_property(self):
        panel = self._make_panel()
        self.assertIsInstance(panel.context, PluginContext)

    def test_plugin_path_property(self):
        panel = self._make_panel()
        self.assertEqual(panel.plugin_path, "/plugins/test")

    def test_preset_device_name(self):
        panel = self._make_panel()
        # Patch title property since SettingsPanel wasn't fully initialized
        with patch.object(type(panel), "title", new_callable=lambda: property(lambda self: "GX 100 Shifter")):
            self.assertEqual(panel.preset_device_name, "gx-100-shifter")

    def test_preset_device_name_simple(self):
        panel = self._make_panel()
        with patch.object(type(panel), "title", new_callable=lambda: property(lambda self: "MyDevice")):
            self.assertEqual(panel.preset_device_name, "mydevice")

    def test_on_device_connected_tracks_device(self):
        panel = self._make_panel()
        device = PluginDeviceInfo("Dev", 1, 2, "/dev/input/event0")
        panel.on_device_connected(device)
        self.assertIn("/dev/input/event0", panel._connected_devices)
        self.assertIs(panel._connected_devices["/dev/input/event0"], device)

    def test_on_device_disconnected_removes_device(self):
        panel = self._make_panel()
        device = PluginDeviceInfo("Dev", 1, 2, "/dev/input/event0")
        panel.on_device_connected(device)
        panel.on_device_disconnected(device)
        self.assertNotIn("/dev/input/event0", panel._connected_devices)

    def test_on_device_disconnected_unknown_path(self):
        panel = self._make_panel()
        device = PluginDeviceInfo("Dev", 1, 2, "/dev/input/event99")
        # Should not raise
        panel.on_device_disconnected(device)

    def test_get_preset_settings_default_empty(self):
        panel = self._make_panel()
        self.assertEqual(panel.get_preset_settings(), {})

    def test_on_preset_loaded_default_noop(self):
        panel = self._make_panel()
        # Should not raise
        panel.on_preset_loaded({"key": "value"})

    def test_get_plugin_setting_no_settings(self):
        panel = self._make_panel()
        panel._context.settings_handler.read_setting.return_value = None
        with patch.object(type(panel), "title", new_callable=lambda: property(lambda self: "Test")):
            result = panel.get_plugin_setting("some-key")
        self.assertIsNone(result)

    def test_get_plugin_setting_with_existing_data(self):
        panel = self._make_panel()
        panel._context.settings_handler.read_setting.return_value = {
            "test": {"sensitivity": 80}
        }
        with patch.object(type(panel), "title", new_callable=lambda: property(lambda self: "Test")):
            result = panel.get_plugin_setting("sensitivity")
        self.assertEqual(result, 80)

    def test_set_plugin_setting(self):
        panel = self._make_panel()
        panel._context.settings_handler.read_setting.return_value = {}
        with patch.object(type(panel), "title", new_callable=lambda: property(lambda self: "Test")):
            panel.set_plugin_setting("brightness", 50)

        panel._context.settings_handler.write_setting.assert_called_once_with(
            {"test": {"brightness": 50}}, "plugin-settings"
        )

    def test_set_plugin_setting_preserves_existing(self):
        panel = self._make_panel()
        panel._context.settings_handler.read_setting.return_value = {
            "test": {"existing": 10}
        }
        with patch.object(type(panel), "title", new_callable=lambda: property(lambda self: "Test")):
            panel.set_plugin_setting("new-key", 20)

        panel._context.settings_handler.write_setting.assert_called_once_with(
            {"test": {"existing": 10, "new-key": 20}}, "plugin-settings"
        )

    def test_multiple_devices_connected(self):
        panel = self._make_panel()
        dev1 = PluginDeviceInfo("Dev1", 1, 2, "/dev/input/event0")
        dev2 = PluginDeviceInfo("Dev2", 1, 2, "/dev/input/event1")
        panel.on_device_connected(dev1)
        panel.on_device_connected(dev2)
        self.assertEqual(len(panel._connected_devices), 2)

        panel.on_device_disconnected(dev1)
        self.assertEqual(len(panel._connected_devices), 1)
        self.assertIn("/dev/input/event1", panel._connected_devices)


if __name__ == "__main__":
    unittest.main(verbosity=2)
