#!/usr/bin/env python3
"""
Unit tests for foxblat.pithouse_converter

Tests Pithouse preset validation and conversion to Foxblat format.
"""

import unittest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from foxblat.pithouse_converter import PithouseConverter


def _make_valid_pithouse():
    """Create a minimal valid Pithouse preset dict."""
    return {
        "name": "Test Preset",
        "deviceType": "Motor",
        "deviceParams": {
            "version": 2,
            "gameForceFeedbackReversal": False,
            "gameForceFeedbackStrength": 80,
            "maximumSteeringAngle": 900,
            "safeDrivingEnabled": True,
            "safeDrivingMode": 1,
            "softLimitGameForceStrength": 30,
            "softLimitStiffness": 40,
            "softLimitStrength": 50,
            "speedDependentDamping": 10,
            "initialSpeedDependentDamping": 5,
            "equalizerGain1": 55,
            "equalizerGain2": 60,
            "equalizerGain3": 50,
            "equalizerGain4": 45,
            "equalizerGain5": 50,
            "equalizerGain6": 50,
            "mechanicalDamper": 3,
            "mechanicalFriction": 2,
            "naturalInertiaV2": 4,
            "mechanicalSpringStrength": 1,
            "maximumSteeringSpeed": 5,
            "maximumTorque": 100,
            "setGameDampingValue": 50,
            "setGameFrictionValue": 30,
            "setGameInertiaValue": 20,
            "setGameSpringValue": 40,
            "constForceExtraMode": 1,
            "forceFeedbackMaping": "",
        },
    }


class TestPithouseValidation(unittest.TestCase):
    """Test Pithouse preset validation."""

    def setUp(self):
        self.converter = PithouseConverter()

    def test_valid_preset(self):
        data = _make_valid_pithouse()
        valid, error = self.converter.validate(data)
        self.assertTrue(valid)
        self.assertEqual(error, "")

    def test_invalid_not_dict(self):
        valid, error = self.converter.validate("not a dict")
        self.assertFalse(valid)
        self.assertIn("expected JSON object", error)

    def test_wrong_device_type(self):
        data = _make_valid_pithouse()
        data["deviceType"] = "Pedals"
        valid, error = self.converter.validate(data)
        self.assertFalse(valid)
        self.assertIn("Pedals", error)

    def test_missing_device_type(self):
        data = _make_valid_pithouse()
        del data["deviceType"]
        valid, error = self.converter.validate(data)
        self.assertFalse(valid)
        self.assertIn("unknown", error)

    def test_missing_device_params(self):
        data = _make_valid_pithouse()
        del data["deviceParams"]
        valid, error = self.converter.validate(data)
        self.assertFalse(valid)
        self.assertIn("Missing deviceParams", error)

    def test_wrong_version(self):
        data = _make_valid_pithouse()
        data["deviceParams"]["version"] = 1
        valid, error = self.converter.validate(data)
        self.assertFalse(valid)
        self.assertIn("version", error)

    def test_missing_version(self):
        data = _make_valid_pithouse()
        del data["deviceParams"]["version"]
        valid, error = self.converter.validate(data)
        self.assertFalse(valid)
        self.assertIn("version", error)


class TestPithouseGetName(unittest.TestCase):
    """Test preset name extraction."""

    def setUp(self):
        self.converter = PithouseConverter()

    def test_with_name(self):
        data = {"name": "My Preset"}
        self.assertEqual(self.converter.get_preset_name(data), "My Preset")

    def test_without_name(self):
        data = {}
        self.assertEqual(self.converter.get_preset_name(data), "imported-preset")


class TestPithouseConversion(unittest.TestCase):
    """Test Pithouse to Foxblat preset conversion."""

    def setUp(self):
        self.converter = PithouseConverter()

    def test_convert_has_version(self):
        data = _make_valid_pithouse()
        result = self.converter.convert(data)
        self.assertEqual(result["FoxblatPresetVersion"], "1")

    def test_convert_has_base_and_main(self):
        data = _make_valid_pithouse()
        result = self.converter.convert(data)
        self.assertIn("base", result)
        self.assertIn("main", result)

    def test_base_ffb_strength_scaled(self):
        data = _make_valid_pithouse()
        result = self.converter.convert(data)
        # ffb-strength = value * 10
        self.assertEqual(result["base"]["ffb-strength"], 800)

    def test_base_max_angle(self):
        data = _make_valid_pithouse()
        result = self.converter.convert(data)
        self.assertEqual(result["base"]["max-angle"], 900)

    def test_base_protection_bool(self):
        data = _make_valid_pithouse()
        result = self.converter.convert(data)
        self.assertEqual(result["base"]["protection"], 1)

    def test_base_ffb_reverse_false(self):
        data = _make_valid_pithouse()
        result = self.converter.convert(data)
        self.assertEqual(result["base"]["ffb-reverse"], 0)

    def test_base_mechanical_values_scaled(self):
        data = _make_valid_pithouse()
        result = self.converter.convert(data)
        # damper = mechanicalDamper * 10
        self.assertEqual(result["base"]["damper"], 30)
        self.assertEqual(result["base"]["friction"], 20)
        self.assertEqual(result["base"]["inertia"], 40)
        self.assertEqual(result["base"]["spring"], 10)
        self.assertEqual(result["base"]["speed"], 50)

    def test_base_equalizer(self):
        data = _make_valid_pithouse()
        result = self.converter.convert(data)
        self.assertEqual(result["base"]["equalizer1"], 55)
        self.assertEqual(result["base"]["equalizer2"], 60)

    def test_main_gains_clamped(self):
        data = _make_valid_pithouse()
        data["deviceParams"]["setGameDampingValue"] = 100
        result = self.converter.convert(data)
        # 2.55 * 100 = 255, capped at 255
        self.assertEqual(result["main"]["set-damper-gain"], 255)

    def test_main_gains_scaled(self):
        data = _make_valid_pithouse()
        data["deviceParams"]["setGameDampingValue"] = 50
        result = self.converter.convert(data)
        self.assertEqual(result["main"]["set-damper-gain"], min(round(2.55 * 50), 255))

    def test_main_interpolation(self):
        data = _make_valid_pithouse()
        result = self.converter.convert(data)
        self.assertEqual(result["main"]["set-interpolation"], 1)


class TestFFBCurveDecode(unittest.TestCase):
    """Test FFB curve decoding."""

    def setUp(self):
        self.converter = PithouseConverter()

    def test_empty_mapping_returns_default(self):
        result = self.converter._decode_ffb_curve("")
        self.assertEqual(result["ffb-curve-x1"], 20)
        self.assertEqual(result["ffb-curve-y1"], 20)
        self.assertEqual(result["ffb-curve-y5"], 100)

    def test_short_mapping_returns_default(self):
        result = self.converter._decode_ffb_curve("short")
        self.assertEqual(result["ffb-curve-x1"], 20)

    def test_valid_mapping(self):
        # Create a mapping string with known ord values
        # We need at least 12 chars; curve uses indices 2,3,5,7,9,11
        chars = [chr(i) for i in range(12)]
        mapping = ''.join(chars)
        result = self.converter._decode_ffb_curve(mapping)
        self.assertEqual(result["ffb-curve-x1"], 2)
        self.assertEqual(result["ffb-curve-y1"], 3)
        self.assertEqual(result["ffb-curve-y2"], 5)
        self.assertEqual(result["ffb-curve-y3"], 7)
        self.assertEqual(result["ffb-curve-y4"], 9)
        self.assertEqual(result["ffb-curve-y5"], 11)


class TestLoadAndConvert(unittest.TestCase):
    """Test full file load and convert."""

    def setUp(self):
        self.converter = PithouseConverter()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_valid_file(self):
        data = _make_valid_pithouse()
        filepath = os.path.join(self.tmpdir, "preset.json")
        with open(filepath, "w") as f:
            json.dump(data, f)

        result, name, error = self.converter.load_and_convert(filepath)
        self.assertIsNotNone(result)
        self.assertEqual(name, "Test Preset")
        self.assertEqual(error, "")
        self.assertIn("base", result)

    def test_invalid_json_file(self):
        filepath = os.path.join(self.tmpdir, "bad.json")
        with open(filepath, "w") as f:
            f.write("{invalid json")

        result, name, error = self.converter.load_and_convert(filepath)
        self.assertIsNone(result)
        self.assertIn("Invalid JSON", error)

    def test_missing_file(self):
        result, name, error = self.converter.load_and_convert("/nonexistent/file.json")
        self.assertIsNone(result)
        self.assertIn("Failed to read", error)

    def test_validation_failure(self):
        data = {"deviceType": "Pedals"}
        filepath = os.path.join(self.tmpdir, "pedals.json")
        with open(filepath, "w") as f:
            json.dump(data, f)

        result, name, error = self.converter.load_and_convert(filepath)
        self.assertIsNone(result)
        self.assertIn("Pedals", error)


if __name__ == "__main__":
    unittest.main(verbosity=2)
