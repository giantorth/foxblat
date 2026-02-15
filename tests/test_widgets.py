#!/usr/bin/env python3
"""
Unit tests for foxblat.widgets

Tests the widget/control classes that plugins use to build UIs.
These tests require GTK to be available and will be skipped otherwise.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Try to initialize GTK — skip all tests if unavailable
try:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gtk, Adw, GLib

    # Initialize Adw (which also initializes GTK)
    _app = Adw.Application()
    GTK_AVAILABLE = True
except Exception:
    GTK_AVAILABLE = False


def requires_gtk(cls):
    """Class decorator to skip entire test class if GTK is unavailable."""
    if not GTK_AVAILABLE:
        return unittest.skip("GTK/Adw not available")(cls)
    return cls


@requires_gtk
class TestFoxblatRow(unittest.TestCase):
    """Test cases for the FoxblatRow base class."""

    @classmethod
    def setUpClass(cls):
        from foxblat.widgets.row import FoxblatRow
        cls.FoxblatRow = FoxblatRow

    def test_creation(self):
        row = self.FoxblatRow(title="Test", subtitle="Sub")
        self.assertEqual(row.get_title(), "Test")
        self.assertEqual(row.get_subtitle(), "Sub")

    def test_default_value_is_zero(self):
        row = self.FoxblatRow()
        self.assertEqual(row.get_value(), 0)

    def test_get_active_default_true(self):
        row = self.FoxblatRow()
        self.assertTrue(row.get_active())

    def test_mute_and_unmute(self):
        row = self.FoxblatRow()
        row.mute()
        self.assertTrue(row._mute.is_set())
        row.unmute()
        self.assertFalse(row._mute.is_set())

    def test_mute_with_false(self):
        row = self.FoxblatRow()
        row.mute(True)
        self.assertTrue(row._mute.is_set())
        row.mute(False)
        self.assertFalse(row._mute.is_set())

    def test_expression_default(self):
        row = self.FoxblatRow()
        self.assertEqual(row._expression, "*1")
        self.assertEqual(row._reverse_expression, "*1")

    def test_set_expression(self):
        row = self.FoxblatRow()
        row.set_expression("*2")
        self.assertEqual(row._expression, "*2")

    def test_set_reverse_expression(self):
        row = self.FoxblatRow()
        row.set_reverse_expression("/2")
        self.assertEqual(row._reverse_expression, "/2")

    def test_cooldown_initially_zero(self):
        row = self.FoxblatRow()
        self.assertFalse(row.cooldown())

    def test_cooldown_after_notify(self):
        row = self.FoxblatRow()
        # _notify sets cooldown and dispatches
        row._notify()
        self.assertTrue(row.cooldown())
        # After cooldown consumed, should be false
        self.assertFalse(row.cooldown())

    def test_notify_muted_does_not_dispatch(self):
        results = []
        row = self.FoxblatRow()
        row.subscribe(lambda v: results.append(v))
        row.mute()
        row._notify()
        self.assertEqual(results, [])

    def test_notify_unmuted_dispatches(self):
        results = []
        row = self.FoxblatRow()
        row.subscribe(lambda v: results.append(v))
        row._notify()
        self.assertEqual(results, [0])  # default get_value() returns 0

    def test_disable_cooldown(self):
        row = self.FoxblatRow()
        row.disable_cooldown()
        row._notify()
        self.assertFalse(row.cooldown())

    def test_shutdown(self):
        row = self.FoxblatRow()
        self.assertFalse(row._shutdown)
        row.shutdown()
        self.assertTrue(row._shutdown)

    def test_set_value_directly(self):
        row = self.FoxblatRow()
        # _set_value is a no-op on base class, but set_value_directly should not raise
        row.set_value_directly(42)

    def test_set_value_none_ignored(self):
        row = self.FoxblatRow()
        # Should not raise
        row.set_value(None)


@requires_gtk
class TestFoxblatSliderRow(unittest.TestCase):
    """Test cases for FoxblatSliderRow."""

    @classmethod
    def setUpClass(cls):
        from foxblat.widgets.slider_row import FoxblatSliderRow
        cls.SliderRow = FoxblatSliderRow

    def test_creation_default(self):
        row = self.SliderRow(title="Volume", range_start=0, range_end=100, value=50)
        self.assertEqual(row.get_title(), "Volume")

    def test_get_raw_value(self):
        row = self.SliderRow(title="Test", range_start=0, range_end=100, value=50)
        self.assertEqual(row.get_raw_value(), 50)

    def test_get_value_default_expression(self):
        row = self.SliderRow(title="Test", range_start=0, range_end=100, value=75)
        self.assertEqual(row.get_value(), 75)

    def test_get_value_with_expression(self):
        row = self.SliderRow(title="Test", range_start=0, range_end=100, value=50)
        row.set_expression("*2")
        self.assertEqual(row.get_value(), 100)

    def test_set_value_directly(self):
        row = self.SliderRow(title="Test", range_start=0, range_end=100, value=0)
        row.set_value_directly(80)
        self.assertEqual(row.get_raw_value(), 80)

    def test_set_value_with_reverse_expression(self):
        row = self.SliderRow(title="Test", range_start=0, range_end=100, value=0)
        row.set_reverse_expression("/2")
        row.set_value_directly(80)
        self.assertEqual(row.get_raw_value(), 40)

    def test_set_value_clamps_below_range(self):
        row = self.SliderRow(title="Test", range_start=10, range_end=100, value=50)
        row.set_value_directly(5)
        self.assertEqual(row.get_raw_value(), 10)

    def test_subscribe_on_change(self):
        results = []
        row = self.SliderRow(title="Test", range_start=0, range_end=100, value=0)
        row.subscribe(lambda v: results.append(v))
        row.set_value_directly(50)
        self.assertEqual(results, [50])

    def test_slider_marks(self):
        # Should not raise
        row = self.SliderRow(title="Test", range_start=0, range_end=100, value=0)
        row.add_marks(0, 25, 50, 75, 100)

    def test_slider_width(self):
        row = self.SliderRow(title="Test", range_start=0, range_end=100, value=0)
        row.set_slider_width(400)


@requires_gtk
class TestFoxblatSwitchRow(unittest.TestCase):
    """Test cases for FoxblatSwitchRow."""

    @classmethod
    def setUpClass(cls):
        from foxblat.widgets.switch_row import FoxblatSwitchRow
        cls.SwitchRow = FoxblatSwitchRow

    def test_creation(self):
        row = self.SwitchRow(title="Enable")
        self.assertEqual(row.get_title(), "Enable")

    def test_default_value_off(self):
        row = self.SwitchRow(title="Test")
        self.assertEqual(row.get_value(), 0)

    def test_set_and_get_value(self):
        row = self.SwitchRow(title="Test")
        row.set_value_directly(1)
        self.assertEqual(row.get_value(), 1)

    def test_set_value_on_off(self):
        row = self.SwitchRow(title="Test")
        row.set_value_directly(1)
        self.assertEqual(row.get_value(), 1)
        row.set_value_directly(0)
        self.assertEqual(row.get_value(), 0)

    def test_reverse_values(self):
        row = self.SwitchRow(title="Test")
        row.reverse_values()
        # With reverse: set_value(1) turns switch OFF, get_value reverses OFF→1
        row.set_value_directly(1)
        self.assertEqual(row.get_value(), 1)
        # With reverse: set_value(0) turns switch ON, get_value reverses ON→0
        row.set_value_directly(0)
        self.assertEqual(row.get_value(), 0)

    def test_set_value_negative_ignored(self):
        row = self.SwitchRow(title="Test")
        row.set_value_directly(1)
        row.set_value_directly(-1)
        # Value should remain 1 since negative is ignored
        self.assertEqual(row.get_value(), 1)

    def test_subscribe_on_toggle(self):
        results = []
        row = self.SwitchRow(title="Test")
        row.subscribe(lambda v: results.append(v))
        row.set_value_directly(1)
        self.assertIn(1, results)


@requires_gtk
class TestFoxblatButtonRow(unittest.TestCase):
    """Test cases for FoxblatButtonRow."""

    @classmethod
    def setUpClass(cls):
        from foxblat.widgets.button_row import FoxblatButtonRow
        cls.ButtonRow = FoxblatButtonRow

    def test_creation_with_label(self):
        row = self.ButtonRow(title="Action", button_label="Click Me")
        self.assertEqual(row.get_title(), "Action")

    def test_creation_without_label(self):
        row = self.ButtonRow(title="Action")
        self.assertEqual(row.get_title(), "Action")

    def test_get_value(self):
        row = self.ButtonRow(title="Test", button_label="Go")
        self.assertEqual(row.get_value(), 1)

    def test_add_button(self):
        row = self.ButtonRow(title="Test")
        button = row.add_button("Button 1")
        self.assertIsNotNone(button)

    def test_add_button_with_callback(self):
        results = []
        row = self.ButtonRow(title="Test")
        row.add_button("Click", callback=lambda: results.append("clicked"))


@requires_gtk
class TestFoxblatLabelRow(unittest.TestCase):
    """Test cases for FoxblatLabelRow."""

    @classmethod
    def setUpClass(cls):
        from foxblat.widgets.label_row import FoxblatLabelRow
        cls.LabelRow = FoxblatLabelRow

    def test_creation(self):
        row = self.LabelRow(title="Status", value="OK")
        self.assertEqual(row.get_title(), "Status")
        self.assertEqual(row.get_label(), "OK")

    def test_set_label(self):
        row = self.LabelRow(title="Status", value="")
        # set_label uses GLib.idle_add, so call internal label directly
        row._label.set_label("Connected")
        self.assertEqual(row.get_label(), "Connected")

    def test_set_suffix(self):
        row = self.LabelRow(title="Speed", value="100")
        row.set_suffix(" km/h")
        self.assertEqual(row._suffix, " km/h")

    def test_set_value_with_suffix(self):
        row = self.LabelRow(title="Speed", value="0")
        row.set_suffix(" rpm")
        row._set_value(100)
        self.assertEqual(row.get_label(), "100 rpm")


@requires_gtk
class TestFoxblatToggleButtonRow(unittest.TestCase):
    """Test cases for FoxblatToggleButtonRow."""

    @classmethod
    def setUpClass(cls):
        from foxblat.widgets.toggle_button_row import FoxblatToggleButtonRow
        cls.ToggleRow = FoxblatToggleButtonRow

    def test_creation(self):
        row = self.ToggleRow(title="Mode")
        self.assertEqual(row.get_title(), "Mode")

    def test_add_buttons(self):
        row = self.ToggleRow(title="Mode")
        row.add_buttons("A", "B", "C")
        self.assertEqual(len(row._buttons), 3)

    def test_get_value_default(self):
        row = self.ToggleRow(title="Mode")
        row.add_buttons("A", "B")
        self.assertEqual(row.get_value(), 0)

    def test_set_value(self):
        row = self.ToggleRow(title="Mode")
        row.add_buttons("A", "B", "C")
        row._set_value(2)
        self.assertEqual(row.get_value(), 2)

    def test_set_value_clamps_high(self):
        row = self.ToggleRow(title="Mode")
        row.add_buttons("A", "B")
        row._set_value(10)
        self.assertEqual(row.get_value(), 1)  # clamped to last index

    def test_set_value_clamps_low(self):
        row = self.ToggleRow(title="Mode")
        row.add_buttons("A", "B")
        row._set_value(-5)
        self.assertEqual(row.get_value(), 0)  # clamped to 0

    def test_set_value_minus_one_deselects(self):
        row = self.ToggleRow(title="Mode")
        row.add_buttons("A", "B")
        row._set_value(1)
        row._set_value(-1)
        # All buttons should be inactive
        for button in row._buttons:
            self.assertFalse(button.get_active())


@requires_gtk
class TestFoxblatComboRow(unittest.TestCase):
    """Test cases for FoxblatComboRow."""

    @classmethod
    def setUpClass(cls):
        from foxblat.widgets.combo_row import FoxblatComboRow
        cls.ComboRow = FoxblatComboRow

    def test_creation(self):
        row = self.ComboRow(title="Select")
        self.assertEqual(row.get_title(), "Select")

    def test_add_entries(self):
        row = self.ComboRow(title="Select")
        row.add_entries("Option A", "Option B", "Option C")
        model = row.get_model()
        self.assertEqual(model.get_n_items(), 3)

    def test_add_empty_entry_ignored(self):
        row = self.ComboRow(title="Select")
        row.add_entry("")
        self.assertEqual(row.get_model().get_n_items(), 0)

    def test_get_value(self):
        row = self.ComboRow(title="Select")
        row.add_entries("A", "B")
        self.assertEqual(row.get_value(), 0)

    def test_set_value(self):
        row = self.ComboRow(title="Select")
        row.add_entries("A", "B", "C")
        row._set_value(2)
        self.assertEqual(row.get_value(), 2)

    def test_set_value_negative_ignored(self):
        row = self.ComboRow(title="Select")
        row.add_entries("A", "B")
        row._set_value(1)
        row._set_value(-1)
        self.assertEqual(row.get_value(), 1)


@requires_gtk
class TestFoxblatLevelRow(unittest.TestCase):
    """Test cases for FoxblatLevelRow."""

    @classmethod
    def setUpClass(cls):
        from foxblat.widgets.level_row import FoxblatLevelRow
        cls.LevelRow = FoxblatLevelRow

    def test_creation(self):
        row = self.LevelRow(title="Level", max_value=100)
        self.assertEqual(row.get_title(), "Level")

    def test_get_value_default_zero(self):
        row = self.LevelRow(title="Level", max_value=100)
        self.assertEqual(row.get_value(), 0)

    def test_set_and_get_value(self):
        row = self.LevelRow(title="Level", max_value=100)
        row._set_value(50)
        self.assertEqual(row.get_value(), 50)

    def test_value_clamped_to_max(self):
        row = self.LevelRow(title="Level", max_value=100)
        row._set_value(200)
        self.assertEqual(row.get_value(), 100)

    def test_value_clamped_to_zero(self):
        row = self.LevelRow(title="Level", max_value=100)
        row._set_value(-10)
        self.assertEqual(row.get_value(), 0)

    def test_get_fraction(self):
        row = self.LevelRow(title="Level", max_value=100)
        row._set_value(50)
        self.assertAlmostEqual(row.get_fraction(), 0.5)

    def test_get_percent(self):
        row = self.LevelRow(title="Level", max_value=200)
        row._set_value(100)
        self.assertEqual(row.get_percent(), 50)

    def test_set_bar_max(self):
        row = self.LevelRow(title="Level", max_value=100)
        row.set_bar_max(200)
        self.assertEqual(row._max_value, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
