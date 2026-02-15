#!/usr/bin/env python3
"""
Unit tests for foxblat.hid_handler

Tests MozaHidDevice patterns, AxisValue, BlipData, is_moza_device(),
and HidHandler pure logic. Device I/O is mocked.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from foxblat.hid_handler import (
    MozaHidDevice, MozaAxis, AxisValue, BlipData,
    is_moza_device, MOZA_AXIS_LIST, MOZA_BUTTON_COUNT,
    MOZA_AXIS_CODES, MOZA_AXIS_BASE_CODES, HidHandler,
)


class TestIsMozaDevice(unittest.TestCase):
    """Test device name pattern matching."""

    def test_base_device(self):
        self.assertTrue(is_moza_device("Gudsen Moza R12 Ultra Base"))
        self.assertTrue(is_moza_device("Gudsen R5 Base"))
        self.assertTrue(is_moza_device("Gudsen R16 Racing Wheel and Pedals"))

    def test_pedals(self):
        self.assertTrue(is_moza_device("Gudsen MOZA SRP Pedals"))
        self.assertTrue(is_moza_device("Gudsen MOZA CRP2 Pedals"))
        self.assertTrue(is_moza_device("Gudsen MOZA SR-P Pedals"))

    def test_handbrake(self):
        self.assertTrue(is_moza_device("HBP Handbrake"))

    def test_hpattern(self):
        self.assertTrue(is_moza_device("HGP Shifter"))

    def test_sequential(self):
        self.assertTrue(is_moza_device("SGP Shifter"))

    def test_hub(self):
        self.assertTrue(is_moza_device("Gudsen Universal Hub"))

    def test_stalks(self):
        self.assertTrue(is_moza_device("MOZA Multi-Function Stalk"))

    def test_non_moza_device(self):
        self.assertFalse(is_moza_device("Logitech G29"))
        self.assertFalse(is_moza_device("Fanatec CSL DD"))
        self.assertFalse(is_moza_device("Generic USB Gamepad"))

    def test_case_insensitive(self):
        self.assertTrue(is_moza_device("GUDSEN MOZA R12 ULTRA BASE"))
        self.assertTrue(is_moza_device("gudsen moza r12 ultra base"))


class TestAxisValue(unittest.TestCase):
    """Test AxisValue thread-safe value holder."""

    def test_creation(self):
        av = AxisValue("steering")
        self.assertEqual(av.name, "steering")
        self.assertEqual(av.value, 0)

    def test_set_and_get(self):
        av = AxisValue("throttle")
        av.value = 500
        self.assertEqual(av.value, 500)

    def test_data_property(self):
        av = AxisValue("brake")
        av.value = 100
        name, value = av.data
        self.assertEqual(name, "brake")
        self.assertEqual(value, 100)


class TestBlipData(unittest.TestCase):
    """Test BlipData configuration class."""

    def test_defaults(self):
        blip = BlipData()
        self.assertFalse(blip.enabled)
        self.assertEqual(blip.level, 0)
        self.assertEqual(blip.duration, 0)

    def test_check_disabled(self):
        blip = BlipData()
        self.assertFalse(blip.check())

    def test_check_enabled_but_zero_level(self):
        blip = BlipData()
        blip.enabled = True
        blip.duration = 100
        self.assertFalse(blip.check())

    def test_check_enabled_but_zero_duration(self):
        blip = BlipData()
        blip.enabled = True
        blip.level = 50
        self.assertFalse(blip.check())

    def test_check_fully_configured(self):
        blip = BlipData()
        blip.enabled = True
        blip.level = 50
        blip.duration = 100
        self.assertTrue(blip.check())

    def test_copy(self):
        source = BlipData()
        source.enabled = True
        source.level = 75
        source.duration = 200

        target = BlipData()
        target.copy(source)
        self.assertTrue(target.enabled)
        self.assertEqual(target.level, 75)
        self.assertEqual(target.duration, 200)


class TestMozaHidDevicePatterns(unittest.TestCase):
    """Test that device pattern constants are valid regex patterns."""

    def test_patterns_are_strings(self):
        import re
        patterns = [
            MozaHidDevice.BASE, MozaHidDevice.PEDALS, MozaHidDevice.HANDBRAKE,
            MozaHidDevice.HPATTERN, MozaHidDevice.SEQUENTIAL, MozaHidDevice.HUB,
            MozaHidDevice.STALKS,
        ]
        for pattern in patterns:
            self.assertIsInstance(pattern, str)
            # Should compile without error
            re.compile(pattern)


class TestMozaAxisConstants(unittest.TestCase):
    """Test axis constant definitions."""

    def test_axis_list_completeness(self):
        self.assertIn("steering", MOZA_AXIS_LIST)
        self.assertIn("throttle", MOZA_AXIS_LIST)
        self.assertIn("brake", MOZA_AXIS_LIST)
        self.assertIn("clutch", MOZA_AXIS_LIST)
        self.assertIn("handbrake", MOZA_AXIS_LIST)

    def test_axis_data_attributes(self):
        self.assertEqual(MozaAxis.STEERING.name, "steering")
        self.assertEqual(MozaAxis.STEERING.device, MozaHidDevice.BASE)
        self.assertEqual(MozaAxis.THROTTLE.name, "throttle")
        self.assertEqual(MozaAxis.THROTTLE.device, MozaHidDevice.PEDALS)


class TestHidHandler(unittest.TestCase):
    """Test HidHandler initialization and pure logic."""

    def test_construction(self):
        handler = HidHandler()
        self.assertIsNotNone(handler)

    def test_button_events_registered(self):
        handler = HidHandler()
        events = handler.list_events()
        self.assertIn("button-1", events)
        self.assertIn(f"button-{MOZA_BUTTON_COUNT}", events)

    def test_axis_events_registered(self):
        handler = HidHandler()
        events = handler.list_events()
        for axis in MOZA_AXIS_LIST:
            self.assertIn(axis, events)

    def test_gear_event_registered(self):
        handler = HidHandler()
        self.assertIn("gear", handler.list_events())

    def test_update_rate_default(self):
        handler = HidHandler()
        self.assertEqual(handler.get_update_rate(), 120)

    def test_set_update_rate_valid(self):
        handler = HidHandler()
        self.assertTrue(handler.set_update_rate(60))
        self.assertEqual(handler.get_update_rate(), 60)

    def test_set_update_rate_zero(self):
        handler = HidHandler()
        self.assertTrue(handler.set_update_rate(0))
        self.assertEqual(handler.get_update_rate(), 0)

    def test_set_update_rate_max(self):
        handler = HidHandler()
        self.assertTrue(handler.set_update_rate(1000))
        self.assertEqual(handler.get_update_rate(), 1000)

    def test_set_update_rate_too_high(self):
        handler = HidHandler()
        self.assertFalse(handler.set_update_rate(1001))
        self.assertEqual(handler.get_update_rate(), 120)  # unchanged

    def test_set_update_rate_negative(self):
        handler = HidHandler()
        self.assertFalse(handler.set_update_rate(-1))

    def test_update_blip_data(self):
        handler = HidHandler()
        handler.update_blip_data(enabled=True, level=50, duration=200)
        self.assertTrue(handler._blip.enabled)
        self.assertEqual(handler._blip.level, 50)
        self.assertEqual(handler._blip.duration, 200)

    def test_update_blip_level_out_of_range(self):
        handler = HidHandler()
        handler.update_blip_data(level=150)
        self.assertEqual(handler._blip.level, 0)  # unchanged

    def test_update_blip_duration_out_of_range(self):
        handler = HidHandler()
        handler.update_blip_data(duration=2000)
        self.assertEqual(handler._blip.duration, 0)  # unchanged

    def test_update_blip_partial(self):
        handler = HidHandler()
        handler.update_blip_data(level=50)
        self.assertFalse(handler._blip.enabled)  # unchanged
        self.assertEqual(handler._blip.level, 50)

    def test_copy_blip_data(self):
        handler = HidHandler()
        source = BlipData()
        source.enabled = True
        source.level = 80
        source.duration = 300
        handler.copy_blip_data(source)
        self.assertTrue(handler._blip.enabled)
        self.assertEqual(handler._blip.level, 80)
        self.assertEqual(handler._blip.duration, 300)

    def test_hpattern_connected(self):
        handler = HidHandler()
        handler.hpattern_connected(True)
        self.assertTrue(handler._hpattern_connected.is_set())
        handler.hpattern_connected(False)
        self.assertFalse(handler._hpattern_connected.is_set())

    def test_stalks_turnsignal_compat(self):
        handler = HidHandler()
        handler.stalks_turnsignal_compat_active(True)
        self.assertTrue(handler._stalks_turnsignal_compat)
        handler.stalks_turnsignal_compat_active(False)
        self.assertFalse(handler._stalks_turnsignal_compat)

    def test_stalks_turnsignal_compat_constant(self):
        handler = HidHandler()
        handler.stalks_turnsignal_compat_constant_active(True)
        self.assertTrue(handler._stalks_turnsignal_compat_constant)

    def test_stalks_headlights_compat(self):
        handler = HidHandler()
        handler.stalks_headlights_compat_active(True)
        self.assertTrue(handler._stalks_headlights_compat)

    def test_stalks_wipers_compat_mutual_exclusion(self):
        handler = HidHandler()
        handler.stalks_wipers_compat_active(True)
        self.assertTrue(handler._stalks_wipers_compat)
        # Enabling compat2 should disable compat
        handler.stalks_wipers_compat2_active(True)
        self.assertFalse(handler._stalks_wipers_compat)
        self.assertTrue(handler._stalks_wipers_compat2)

    def test_stalks_wipers_compat_reverse_exclusion(self):
        handler = HidHandler()
        handler.stalks_wipers_compat2_active(True)
        handler.stalks_wipers_compat_active(True)
        self.assertTrue(handler._stalks_wipers_compat)
        self.assertFalse(handler._stalks_wipers_compat2)

    def test_paddle_sync(self):
        handler = HidHandler()
        handler.paddle_sync_enabled(True)
        self.assertTrue(handler._paddle_sync)
        handler.paddle_sync_enabled(False)
        self.assertFalse(handler._paddle_sync)

    def test_paddle_sync_no_op_same_value(self):
        handler = HidHandler()
        handler.paddle_sync_enabled(False)
        handler.paddle_sync_enabled(False)
        self.assertFalse(handler._paddle_sync)

    def test_stalks_ignition(self):
        handler = HidHandler()
        handler.stalks_ignition_active(True)
        self.assertTrue(handler._stalks_ignition)
        self.assertFalse(handler._ignition_state)

    def test_detection_fix_flag(self):
        handler = HidHandler()
        handler.set_detection_fix_enabled(True)
        self.assertTrue(handler._detection_fix)

    def test_stop(self):
        handler = HidHandler()
        handler._running.set()
        handler.stop()
        self.assertFalse(handler._running.is_set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
