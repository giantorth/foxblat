#!/usr/bin/env python3
# Copyright (c) 2026, R. Orth (giantorth)
"""
Unit tests for foxblat.bitwise

Tests bit manipulation utility functions.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from foxblat import bitwise
from foxblat.bitwise import modify_bit, set_bit, unset_bit, toggle_bit, bit, swap_nibbles

# Alias to avoid pytest collecting the bare function as a test
check_bit = bitwise.test_bit


class TestTestBit(unittest.TestCase):
    """Test cases for check_bit()."""

    def test_bit_set(self):
        self.assertTrue(check_bit(0b1010, 1))
        self.assertTrue(check_bit(0b1010, 3))

    def test_bit_not_set(self):
        self.assertFalse(check_bit(0b1010, 0))
        self.assertFalse(check_bit(0b1010, 2))

    def test_bit_zero_value(self):
        self.assertFalse(check_bit(0, 0))
        self.assertFalse(check_bit(0, 7))

    def test_bit_all_ones(self):
        self.assertTrue(check_bit(0xFF, 0))
        self.assertTrue(check_bit(0xFF, 7))

    def test_negative_bit_number(self):
        self.assertIsNone(check_bit(0xFF, -1))

    def test_high_bit(self):
        self.assertTrue(check_bit(1 << 31, 31))
        self.assertFalse(check_bit(1 << 31, 30))


class TestModifyBit(unittest.TestCase):
    """Test cases for modify_bit()."""

    def test_set_bit(self):
        self.assertEqual(modify_bit(0, 0, set_bit=True), 1)
        self.assertEqual(modify_bit(0, 3, set_bit=True), 8)

    def test_unset_bit(self):
        self.assertEqual(modify_bit(0xFF, 0, set_bit=False), 0xFE)
        self.assertEqual(modify_bit(0xFF, 7, set_bit=False), 0x7F)

    def test_set_already_set(self):
        self.assertEqual(modify_bit(0b1111, 2, set_bit=True), 0b1111)

    def test_unset_already_unset(self):
        self.assertEqual(modify_bit(0, 5, set_bit=False), 0)

    def test_negative_bit_number(self):
        self.assertIsNone(modify_bit(0, -1))


class TestSetBit(unittest.TestCase):
    """Test cases for set_bit()."""

    def test_set_bit_zero(self):
        self.assertEqual(set_bit(0, 0), 1)

    def test_set_bit_three(self):
        self.assertEqual(set_bit(0, 3), 8)

    def test_set_bit_preserves_others(self):
        self.assertEqual(set_bit(0b0101, 1), 0b0111)


class TestUnsetBit(unittest.TestCase):
    """Test cases for unset_bit()."""

    def test_unset_bit_zero(self):
        self.assertEqual(unset_bit(1, 0), 0)

    def test_unset_bit_preserves_others(self):
        self.assertEqual(unset_bit(0b1111, 2), 0b1011)


class TestToggleBit(unittest.TestCase):
    """Test cases for toggle_bit()."""

    def test_toggle_off_to_on(self):
        self.assertEqual(toggle_bit(0, 0), 1)

    def test_toggle_on_to_off(self):
        self.assertEqual(toggle_bit(1, 0), 0)

    def test_toggle_preserves_others(self):
        self.assertEqual(toggle_bit(0b1010, 0), 0b1011)
        self.assertEqual(toggle_bit(0b1010, 1), 0b1000)

    def test_double_toggle_identity(self):
        value = 0xAB
        self.assertEqual(toggle_bit(toggle_bit(value, 4), 4), value)


class TestBit(unittest.TestCase):
    """Test cases for bit()."""

    def test_bit_0(self):
        self.assertEqual(bit(0), 1)

    def test_bit_7(self):
        self.assertEqual(bit(7), 128)

    def test_bit_15(self):
        self.assertEqual(bit(15), 32768)


class TestSwapNibbles(unittest.TestCase):
    """Test cases for swap_nibbles()."""

    def test_basic_swap(self):
        self.assertEqual(swap_nibbles(0xAB), 0xBA)

    def test_zero(self):
        self.assertEqual(swap_nibbles(0x00), 0x00)

    def test_ff(self):
        self.assertEqual(swap_nibbles(0xFF), 0xFF)

    def test_low_nibble_only(self):
        self.assertEqual(swap_nibbles(0x0F), 0xF0)

    def test_high_nibble_only(self):
        self.assertEqual(swap_nibbles(0xF0), 0x0F)

    def test_asymmetric(self):
        self.assertEqual(swap_nibbles(0x12), 0x21)

    def test_double_swap_identity(self):
        value = 0x3C
        self.assertEqual(swap_nibbles(swap_nibbles(value)), value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
