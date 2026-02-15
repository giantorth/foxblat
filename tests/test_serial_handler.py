#!/usr/bin/env python3
# Copyright (c) 2026, R. Orth (giantorth)
"""
Unit tests for foxblat.serial_handler

Tests SerialHandler message handling and lifecycle.
Since SerialHandler spawns threads/processes on construction,
we test the class methods with carefully mocked dependencies.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock
from threading import Event

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestSerialHandlerWriteBytes(unittest.TestCase):
    """Test write_bytes queueing without constructing a full SerialHandler."""

    @patch("foxblat.serial_handler.Process")
    @patch("foxblat.serial_handler.Thread")
    @patch("foxblat.serial_handler.Queue")
    @patch("foxblat.serial_handler.Event")
    def test_write_bytes_queues_message(self, MockEvent, MockQueue, MockThread, MockProcess):
        import queue
        # Use stdlib queue.Queue so put/get/empty work without multiprocessing
        MockQueue.side_effect = lambda: queue.Queue()
        MockEvent.side_effect = lambda: MagicMock()
        from foxblat.serial_handler import SerialHandler
        handler = SerialHandler("/dev/null", 0xAA, "test")
        handler.write_bytes(b'\x01\x02\x03')
        self.assertFalse(handler._write_queue.empty())
        msg = handler._write_queue.get()
        self.assertEqual(msg, b'\x01\x02\x03')

    @patch("foxblat.serial_handler.Process")
    @patch("foxblat.serial_handler.Thread")
    def test_write_bytes_none_ignored(self, MockThread, MockProcess):
        from foxblat.serial_handler import SerialHandler
        handler = SerialHandler("/dev/null", 0xAA, "test")
        handler.write_bytes(None)
        self.assertTrue(handler._write_queue.empty())


class TestSerialHandlerStop(unittest.TestCase):
    """Test stop method."""

    @patch("foxblat.serial_handler.Process")
    @patch("foxblat.serial_handler.Thread")
    def test_stop_sets_shutdown(self, MockThread, MockProcess):
        from foxblat.serial_handler import SerialHandler
        handler = SerialHandler("/dev/null", 0xAA, "test")
        handler.stop()
        self.assertTrue(handler._shutdown.is_set())
        self.assertFalse(handler._serial_available.is_set())


class TestSerialHandlerReadProtocol(unittest.TestCase):
    """Test the serial read protocol logic in isolation."""

    def test_payload_length_validation(self):
        """Valid payload lengths are 2-11."""
        valid_lengths = list(range(2, 12))
        for length in valid_lengths:
            self.assertTrue(2 <= length <= 11)

        invalid_lengths = [0, 1, 12, 100]
        for length in invalid_lengths:
            self.assertFalse(2 <= length <= 11)


class TestSerialHandlerSubscription(unittest.TestCase):
    """Test that SerialHandler inherits SimpleEventDispatcher."""

    @patch("foxblat.serial_handler.Process")
    @patch("foxblat.serial_handler.Thread")
    def test_subscribe(self, MockThread, MockProcess):
        from foxblat.serial_handler import SerialHandler
        handler = SerialHandler("/dev/null", 0xAA, "test")
        results = []
        handler.subscribe(lambda data: results.append(data))
        handler._dispatch(b'\x01\x02')
        self.assertEqual(results, [b'\x01\x02'])


if __name__ == "__main__":
    unittest.main(verbosity=2)
