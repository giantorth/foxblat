#!/usr/bin/env python3
"""
Unit tests for foxblat.connection_manager

Tests MozaSerialDevice, MozaConnectionManager command parsing,
device ID handling, and event registration.
Uses mocked serial data YAML and serial handlers.
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

# Minimal serial data YAML for testing
MOCK_SERIAL_DATA = {
    "message-start": 170,
    "magic-value": 0,
    "device-ids": {
        "base": 16,
        "main": 18,
        "wheel": 32,
        "pedals": 48,
        "hub": -1,
    },
    "ids-to-names": {
        16: "base",
        32: "wheel",
    },
    "commands": {
        "base": {
            "max-angle": {"id": [1], "read": 10, "write": 20, "bytes": 2, "type": "int"},
            "ffb-strength": {"id": [2], "read": 11, "write": 21, "bytes": 1, "type": "int"},
        },
        "wheel": {
            "rpm-mode": {"id": [16], "read": 63, "write": 30, "bytes": 1, "type": "int"},
        },
        "pedals": {
            "throttle-min": {"id": [1], "read": 40, "write": 50, "bytes": 2, "type": "int"},
            "read-only": {"id": [2], "read": 41, "write": -1, "bytes": 1, "type": "int"},
        },
    },
}


def _create_serial_data_file(tmpdir):
    """Write mock serial data YAML to temp dir."""
    filepath = os.path.join(tmpdir, "serial_data.yml")
    with open(filepath, "w") as f:
        yaml.safe_dump(MOCK_SERIAL_DATA, f)
    return filepath


class TestMozaSerialDevice(unittest.TestCase):
    """Test MozaSerialDevice data class."""

    def test_construction_defaults(self):
        from foxblat.connection_manager import MozaSerialDevice
        device = MozaSerialDevice()
        self.assertEqual(device.name, "")
        self.assertEqual(device.path, "")
        self.assertIsNone(device.serial_handler)

    def test_construction_with_args(self):
        from foxblat.connection_manager import MozaSerialDevice
        handler = MagicMock()
        device = MozaSerialDevice("base", "/dev/serial/by-id/usb-base", handler)
        self.assertEqual(device.name, "base")
        self.assertEqual(device.path, "/dev/serial/by-id/usb-base")
        self.assertIs(device.serial_handler, handler)


class TestMozaConnectionManagerInit(unittest.TestCase):
    """Test connection manager initialization."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.serial_file = _create_serial_data_file(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_construction(self):
        from foxblat.connection_manager import MozaConnectionManager
        cm = MozaConnectionManager(self.serial_file, dry_run=True)
        self.assertIsNotNone(cm)

    def test_events_registered(self):
        from foxblat.connection_manager import MozaConnectionManager
        cm = MozaConnectionManager(self.serial_file, dry_run=True)
        events = cm.list_events()
        self.assertIn("device-connected", events)
        self.assertIn("device-disconnected", events)
        self.assertIn("hid-device-connected", events)
        self.assertIn("hid-device-disconnected", events)

    def test_command_events_registered(self):
        from foxblat.connection_manager import MozaConnectionManager
        cm = MozaConnectionManager(self.serial_file, dry_run=True)
        events = cm.list_events()
        # Commands with read != -1 should be registered
        self.assertIn("base-max-angle", events)
        self.assertIn("base-ffb-strength", events)
        self.assertIn("wheel-rpm-mode", events)
        self.assertIn("pedals-throttle-min", events)

    def test_hub_skipped_since_id_is_minus_one(self):
        from foxblat.connection_manager import MozaConnectionManager
        cm = MozaConnectionManager(self.serial_file, dry_run=True)
        # hub device_id is -1, so hub commands should not be registered
        events = cm.list_events()
        hub_events = [e for e in events if e.startswith("hub-")]
        self.assertEqual(len(hub_events), 0)

    def test_get_command_data(self):
        from foxblat.connection_manager import MozaConnectionManager
        cm = MozaConnectionManager(self.serial_file, dry_run=True)
        data = cm.get_command_data()
        self.assertIn("base", data)
        self.assertIn("max-angle", data["base"])


class TestMozaConnectionManagerSplitName(unittest.TestCase):
    """Test command name parsing."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.serial_file = _create_serial_data_file(self.tmpdir)
        from foxblat.connection_manager import MozaConnectionManager
        self.cm = MozaConnectionManager(self.serial_file, dry_run=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_valid_command(self):
        name, device = self.cm._split_name("base-max-angle")
        self.assertEqual(name, "max-angle")
        self.assertEqual(device, "base")

    def test_invalid_command(self):
        name, device = self.cm._split_name("nonexistent-command")
        self.assertEqual(name, "")
        self.assertEqual(device, "")


class TestMozaConnectionManagerDeviceId(unittest.TestCase):
    """Test device ID resolution."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.serial_file = _create_serial_data_file(self.tmpdir)
        from foxblat.connection_manager import MozaConnectionManager
        self.cm = MozaConnectionManager(self.serial_file, dry_run=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_base_device_id(self):
        device_id = self.cm.get_device_id("base")
        self.assertEqual(device_id, 16)

    def test_wheel_device_id(self):
        device_id = self.cm.get_device_id("wheel")
        self.assertEqual(device_id, 32)


class TestMozaConnectionManagerCycleWheelId(unittest.TestCase):
    """Test wheel ID cycling logic."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.serial_file = _create_serial_data_file(self.tmpdir)
        from foxblat.connection_manager import MozaConnectionManager
        self.cm = MozaConnectionManager(self.serial_file, dry_run=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_single_call_returns_zero(self):
        # Only calling with old=False — needs both old and new to trigger
        result = self.cm.cycle_wheel_id(old=False)
        self.assertEqual(result, 0)

    def test_both_calls_trigger_cycle(self):
        self.cm.cycle_wheel_id(old=True)
        result = self.cm.cycle_wheel_id(old=False)
        # Should return new wheel ID (wheel_id - 2)
        self.assertIsInstance(result, int)

    def test_cycle_decrements_wheel_id(self):
        original = self.cm._serial_data["device-ids"]["wheel"]
        self.cm.cycle_wheel_id(old=True)
        self.cm.cycle_wheel_id(old=False)
        new_id = self.cm._serial_data["device-ids"]["wheel"]
        self.assertEqual(new_id, original - 2)


class TestMozaConnectionManagerDeviceHandler(unittest.TestCase):
    """Test device handler resolution."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.serial_file = _create_serial_data_file(self.tmpdir)
        from foxblat.connection_manager import MozaConnectionManager, MozaSerialDevice
        self.cm = MozaConnectionManager(self.serial_file, dry_run=True)
        self.MozaSerialDevice = MozaSerialDevice

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_no_devices_returns_none(self):
        handler = self.cm._get_device_handler("base")
        self.assertIsNone(handler)

    def test_with_device(self):
        mock_handler = MagicMock()
        self.cm._serial_devices["base"] = self.MozaSerialDevice("base", "/dev/test", mock_handler)
        handler = self.cm._get_device_handler("base")
        self.assertIs(handler, mock_handler)

    def test_fallback_to_base(self):
        """Non-base devices should fall back to base handler."""
        mock_handler = MagicMock()
        self.cm._serial_devices["base"] = self.MozaSerialDevice("base", "/dev/test", mock_handler)
        handler = self.cm._get_device_handler("pedals")
        self.assertIs(handler, mock_handler)


class TestMozaConnectionManagerHandleSetting(unittest.TestCase):
    """Test _handle_setting for read/write validation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.serial_file = _create_serial_data_file(self.tmpdir)
        from foxblat.connection_manager import MozaConnectionManager, MozaSerialDevice
        self.cm = MozaConnectionManager(self.serial_file, dry_run=True)

        # Add a mock base device so commands can be sent
        mock_handler = MagicMock()
        self.cm._serial_devices["base"] = MozaSerialDevice("base", "/dev/test", mock_handler)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_write_to_read_only_command(self):
        """Writing to a read-only command (write=-1) should not crash."""
        from foxblat.moza_command import MOZA_COMMAND_WRITE
        # pedals read-only has write=-1
        self.cm._handle_setting(42, "read-only", "pedals", MOZA_COMMAND_WRITE)
        # Should not crash, just print a message


class TestMozaConnectionManagerHandleDevices(unittest.TestCase):
    """Test device connection/disconnection handling."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.serial_file = _create_serial_data_file(self.tmpdir)
        from foxblat.connection_manager import MozaConnectionManager, MozaSerialDevice
        self.cm = MozaConnectionManager(self.serial_file, dry_run=True)
        self.MozaSerialDevice = MozaSerialDevice

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    @patch("foxblat.connection_manager.SerialHandler")
    def test_new_device_creates_handler(self, MockSerialHandler):
        mock_instance = MagicMock()
        MockSerialHandler.return_value = mock_instance

        events = []
        self.cm.subscribe("device-connected", lambda name: events.append(name))

        new_devices = {
            "base": self.MozaSerialDevice("base", "/dev/serial/test"),
        }
        self.cm._handle_devices(new_devices)

        MockSerialHandler.assert_called_once()
        self.assertIn("base", events)

    def test_removed_device_stops_handler(self):
        mock_handler = MagicMock()
        self.cm._serial_devices = {
            "base": self.MozaSerialDevice("base", "/dev/old", mock_handler),
        }

        events = []
        self.cm.subscribe("device-disconnected", lambda name: events.append(name))

        self.cm._handle_devices({})  # All devices removed

        mock_handler.stop.assert_called_once()
        self.assertIn("base", events)

    @patch("foxblat.connection_manager.SerialHandler")
    def test_existing_device_reuses_handler(self, MockSerialHandler):
        existing_handler = MagicMock()
        self.cm._serial_devices = {
            "base": self.MozaSerialDevice("base", "/dev/test", existing_handler),
        }

        new_devices = {
            "base": self.MozaSerialDevice("base", "/dev/test"),
        }
        self.cm._handle_devices(new_devices)

        # Should NOT create a new serial handler
        MockSerialHandler.assert_not_called()
        # Should reuse existing handler
        self.assertIs(new_devices["base"].serial_handler, existing_handler)


if __name__ == "__main__":
    unittest.main(verbosity=2)
