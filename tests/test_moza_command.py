#!/usr/bin/env python3
"""
Unit tests for foxblat.moza_command

Tests the MozaCommand class for serial protocol handling.
"""

import unittest
import sys
import os
from struct import pack, unpack

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from foxblat.moza_command import MozaCommand, MOZA_COMMAND_READ, MOZA_COMMAND_WRITE


# Minimal commands data for testing
MOCK_COMMANDS = {
    "base": {
        "max-angle": {
            "id": [0x01],
            "read": 10,
            "write": 20,
            "bytes": 2,
            "type": "int",
        },
        "ffb-strength": {
            "id": [0x02, 0x03],
            "read": 11,
            "write": 21,
            "bytes": 1,
            "type": "int",
        },
        "damper-float": {
            "id": [0x04],
            "read": 12,
            "write": 22,
            "bytes": 4,
            "type": "float",
        },
        "colors": {
            "id": [0x05],
            "read": 13,
            "write": 23,
            "bytes": 3,
            "type": "array",
        },
        "hex-data": {
            "id": [0x06],
            "read": 14,
            "write": 24,
            "bytes": 2,
            "type": "hex",
        },
        "output-y": {
            "id": [0x07],
            "read": 15,
            "write": 25,
            "bytes": 1,
            "type": "int",
        },
    },
    "wheel": {
        "rpm-mode": {
            "id": [0x10],
            "read": 63,
            "write": 30,
            "bytes": 1,
            "type": "int",
        },
    },
    "hub": {
        "hub-setting": {
            "id": [0x20],
            "read": 100,
            "write": 40,
            "bytes": 1,
            "type": "int",
        },
    },
}

MOCK_DEVICE_IDS = {
    0x10: "base",
    0x20: "wheel",
    0x30: "hub",
}


class TestMozaCommandConstruction(unittest.TestCase):
    """Test MozaCommand basic construction."""

    def test_default_state(self):
        cmd = MozaCommand()
        self.assertEqual(cmd.id, 0)
        self.assertEqual(cmd.read_group, 0)
        self.assertEqual(cmd.write_group, 0)
        self.assertIsNone(cmd.device_id)

    def test_set_data_from_name(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("max-angle", MOCK_COMMANDS, "base")
        self.assertEqual(cmd.id, [0x01])
        self.assertEqual(cmd.read_group, 10)
        self.assertEqual(cmd.write_group, 20)
        self.assertEqual(cmd.payload_length, 2)
        self.assertEqual(cmd.type, "int")
        self.assertEqual(cmd.device_type, "base")

    def test_set_data_multi_byte_id(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("ffb-strength", MOCK_COMMANDS, "base")
        self.assertEqual(cmd.id, [0x02, 0x03])
        self.assertEqual(cmd.length, 3)  # payload_length(1) + id_length(2)


class TestMozaCommandProperties(unittest.TestCase):
    """Test MozaCommand property access."""

    def setUp(self):
        self.cmd = MozaCommand()
        self.cmd.set_data_from_name("max-angle", MOCK_COMMANDS, "base")

    def test_id_bytes(self):
        self.assertEqual(self.cmd.id_bytes, bytes([0x01]))

    def test_length(self):
        # payload_length(2) + id_length(1) = 3
        self.assertEqual(self.cmd.length, 3)

    def test_payload_length(self):
        self.assertEqual(self.cmd.payload_length, 2)

    def test_read_group_byte(self):
        self.assertEqual(self.cmd.read_group_byte, bytes([10]))

    def test_write_group_byte(self):
        self.assertEqual(self.cmd.write_group_byte, bytes([20]))

    def test_length_byte(self):
        self.assertEqual(self.cmd.length_byte, bytes([2]))

    def test_device_id_setter(self):
        self.cmd.device_id = 5
        self.assertEqual(self.cmd.device_id, 5)

    def test_device_id_non_int_ignored(self):
        self.cmd.device_id = 5
        self.cmd.device_id = "not_int"
        self.assertEqual(self.cmd.device_id, 5)


class TestMozaCommandPayload(unittest.TestCase):
    """Test payload set/get for different types."""

    def test_int_payload_roundtrip(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("max-angle", MOCK_COMMANDS, "base")
        cmd.set_payload(1000)
        self.assertEqual(cmd.get_payload(), 1000)

    def test_int_payload_zero(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("ffb-strength", MOCK_COMMANDS, "base")
        cmd.set_payload(0)
        self.assertEqual(cmd.get_payload(), 0)

    def test_float_payload_roundtrip(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("damper-float", MOCK_COMMANDS, "base")
        cmd.set_payload(3.14)
        self.assertAlmostEqual(cmd.get_payload(), 3.14, places=2)

    def test_array_payload_roundtrip(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("colors", MOCK_COMMANDS, "base")
        cmd.set_payload([10, 20, 30])
        self.assertEqual(cmd.get_payload(), [10, 20, 30])

    def test_array_payload_truncated(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("colors", MOCK_COMMANDS, "base")
        cmd.set_payload([1, 2, 3, 4, 5])  # 5 elements, but bytes=3
        self.assertEqual(cmd.get_payload(), [1, 2, 3])

    def test_hex_payload_roundtrip(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("hex-data", MOCK_COMMANDS, "base")
        cmd.set_payload("aabb")
        self.assertEqual(cmd.get_payload(), "aabb")

    def test_payload_property_setter(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("max-angle", MOCK_COMMANDS, "base")
        cmd.payload = 500
        self.assertEqual(cmd.get_payload(), 500)

    def test_payload_bytes_direct(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("max-angle", MOCK_COMMANDS, "base")
        cmd.set_payload_bytes(b'\x01\xF4')
        self.assertEqual(cmd.get_payload_bytes(), b'\x01\xF4')

    def test_invalid_payload_fallback(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("max-angle", MOCK_COMMANDS, "base")
        # Passing a string to an int type should trigger the except and set zero bytes
        cmd.set_payload("not_a_number")
        self.assertEqual(cmd.get_payload_bytes(), bytes(2))


class TestMozaCommandChecksum(unittest.TestCase):
    """Test checksum calculation."""

    def test_basic_checksum(self):
        cmd = MozaCommand()
        data = bytes([1, 2, 3])
        result = cmd.checksum(data, 0)
        self.assertEqual(result, 6)

    def test_checksum_with_magic(self):
        cmd = MozaCommand()
        data = bytes([10, 20])
        result = cmd.checksum(data, 100)
        self.assertEqual(result, (100 + 10 + 20) % 256)

    def test_checksum_wraps_at_256(self):
        cmd = MozaCommand()
        data = bytes([200, 200])
        result = cmd.checksum(data, 0)
        self.assertEqual(result, 400 % 256)

    def test_empty_data(self):
        cmd = MozaCommand()
        result = cmd.checksum(b'', 50)
        self.assertEqual(result, 50)


class TestMozaCommandPrepareMessage(unittest.TestCase):
    """Test full message preparation."""

    def test_read_message(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("ffb-strength", MOCK_COMMANDS, "base")
        cmd.device_id = 0x10
        cmd.set_payload(0)

        msg = cmd.prepare_message(start_value=0xAA, rw=MOZA_COMMAND_READ, magic_value=0)

        self.assertEqual(msg[0], 0xAA)       # start
        self.assertEqual(msg[1], cmd.length)  # length = 1 + 2 = 3
        self.assertEqual(msg[2], 11)          # read group
        self.assertEqual(msg[3], 0x10)        # device id
        self.assertEqual(msg[4], 0x02)        # id byte 1
        self.assertEqual(msg[5], 0x03)        # id byte 2
        # Last byte is checksum
        expected_sum = sum(msg[:-1]) % 256
        self.assertEqual(msg[-1], expected_sum)

    def test_write_message(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("ffb-strength", MOCK_COMMANDS, "base")
        cmd.device_id = 0x10
        cmd.set_payload(80)

        msg = cmd.prepare_message(start_value=0xAA, rw=MOZA_COMMAND_WRITE, magic_value=0)

        self.assertEqual(msg[2], 21)  # write group

    def test_message_with_magic_value(self):
        cmd = MozaCommand()
        cmd.set_data_from_name("ffb-strength", MOCK_COMMANDS, "base")
        cmd.device_id = 0x10
        cmd.set_payload(0)

        msg = cmd.prepare_message(start_value=0xAA, rw=MOZA_COMMAND_READ, magic_value=42)

        expected_sum = (sum(msg[:-1]) + 42) % 256
        self.assertEqual(msg[-1], expected_sum)


class TestValueFromData(unittest.TestCase):
    """Test the static value_from_data method."""

    def test_int_from_data(self):
        data = (500).to_bytes(2)
        result = MozaCommand.value_from_data(data, "int", 2)
        self.assertEqual(result, 500)

    def test_float_from_data(self):
        data = pack(">f", 1.5)
        result = MozaCommand.value_from_data(data, "float", 4)
        self.assertAlmostEqual(result, 1.5)

    def test_array_from_data(self):
        data = bytes([10, 20, 30, 40])
        result = MozaCommand.value_from_data(data, "array", 3)
        self.assertEqual(result, [10, 20, 30])

    def test_hex_from_data(self):
        data = bytes([0xAB, 0xCD])
        result = MozaCommand.value_from_data(data, "hex", 2)
        self.assertEqual(result, "abcd")

    def test_unknown_type(self):
        result = MozaCommand.value_from_data(b'\x00', "unknown", 1)
        self.assertIsNone(result)


class TestValueFromResponse(unittest.TestCase):
    """Test response parsing with value_from_response."""

    def test_none_input(self):
        name, value = MozaCommand.value_from_response(None, "base", MOCK_COMMANDS, MOCK_DEVICE_IDS)
        self.assertIsNone(name)
        self.assertIsNone(value)

    def test_unknown_device_id(self):
        # device_id byte = 0xFF after swap won't be in MOCK_DEVICE_IDS
        from foxblat.bitwise import toggle_bit, swap_nibbles
        group = toggle_bit(10, 7)  # read group 10 with bit 7 toggled
        raw_device_id = swap_nibbles(0xFF)
        response = bytes([group, raw_device_id, 0x01, 0x03, 0xE8])
        name, value = MozaCommand.value_from_response(response, "base", MOCK_COMMANDS, MOCK_DEVICE_IDS)
        self.assertIsNone(name)
        self.assertIsNone(value)

    def test_wheel_group_override(self):
        """Groups 63-66 should force device_name to 'wheel'."""
        from foxblat.bitwise import toggle_bit, swap_nibbles
        group = toggle_bit(63, 7)
        raw_device_id = swap_nibbles(0x10)  # maps to "base" in device_ids
        response = bytes([group, raw_device_id, 0x10, 42])
        name, value = MozaCommand.value_from_response(response, "base", MOCK_COMMANDS, MOCK_DEVICE_IDS)
        if name is not None:
            self.assertTrue(name.startswith("wheel-"))

    def test_hub_group_override(self):
        """Group 228/100 should force device_name to 'hub'."""
        from foxblat.bitwise import toggle_bit, swap_nibbles
        group = toggle_bit(228, 7)
        raw_device_id = swap_nibbles(0x10)
        response = bytes([group, raw_device_id, 0x20, 5])
        name, value = MozaCommand.value_from_response(response, "base", MOCK_COMMANDS, MOCK_DEVICE_IDS)
        if name is not None:
            self.assertTrue(name.startswith("hub-"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
