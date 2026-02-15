#!/usr/bin/env python3
# Copyright (c) 2026, R. Orth (giantorth)
"""
Unit tests for foxblat.subscription

Tests the Subscription, SubscriptionList, EventDispatcher,
SimpleEventDispatcher, Observable, and BlockingValue classes.
"""

import unittest
import sys
import os
from threading import Thread
from time import sleep

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from foxblat.subscription import (
    Subscription,
    SubscriptionList,
    EventDispatcher,
    SimpleEventDispatcher,
    Observable,
    BlockingValue,
)


class TestSubscription(unittest.TestCase):
    """Test cases for the Subscription class."""

    def test_call_with_values(self):
        results = []
        sub = Subscription(lambda v: results.append(v))
        sub.call(42)
        self.assertEqual(results, [42])

    def test_call_with_preset_args(self):
        results = []
        sub = Subscription(lambda v, extra: results.append((v, extra)), "extra_arg")
        sub.call(10)
        self.assertEqual(results, [(10, "extra_arg")])

    def test_call_multiple_values(self):
        results = []
        sub = Subscription(lambda a, b: results.append((a, b)))
        sub.call(1, 2)
        self.assertEqual(results, [(1, 2)])

    def test_call_custom_args(self):
        results = []
        sub = Subscription(lambda a, b: results.append((a, b)), "ignored")
        sub.call_custom_args("x", "y")
        self.assertEqual(results, [("x", "y")])


class TestSubscriptionList(unittest.TestCase):
    """Test cases for the SubscriptionList class."""

    def test_append_and_count(self):
        sl = SubscriptionList()
        self.assertEqual(sl.count(), 0)
        sl.append(lambda v: None)
        self.assertEqual(sl.count(), 1)

    def test_append_non_callable_ignored(self):
        sl = SubscriptionList()
        result = sl.append("not a function")
        self.assertIsNone(result)
        self.assertEqual(sl.count(), 0)

    def test_call_invokes_all_subscribers(self):
        results = []
        sl = SubscriptionList()
        sl.append(lambda v: results.append(("a", v)))
        sl.append(lambda v: results.append(("b", v)))
        sl.call(5)
        self.assertEqual(results, [("a", 5), ("b", 5)])

    def test_append_single_fires_once(self):
        results = []
        sl = SubscriptionList()
        sl.append_single(lambda v: results.append(v))
        self.assertEqual(sl.count(), 1)
        sl.call(1)
        self.assertEqual(results, [1])
        # Single-time sub should be consumed
        self.assertEqual(sl.count(), 0)
        sl.call(2)
        self.assertEqual(results, [1])  # not called again

    def test_remove_persistent_subscription(self):
        sl = SubscriptionList()
        sub = sl.append(lambda v: None)
        self.assertEqual(sl.count(), 1)
        sl.remove(sub)
        self.assertEqual(sl.count(), 0)

    def test_remove_single_time_subscription(self):
        sl = SubscriptionList()
        sub = sl.append_single(lambda v: None)
        self.assertEqual(sl.count(), 1)
        sl.remove(sub)
        self.assertEqual(sl.count(), 0)

    def test_clear(self):
        sl = SubscriptionList()
        sl.append(lambda v: None)
        sl.append(lambda v: None)
        sl.append_single(lambda v: None)
        self.assertEqual(sl.count(), 3)
        sl.clear()
        self.assertEqual(sl.count(), 0)

    def test_get(self):
        sl = SubscriptionList()
        sub = sl.append(lambda v: None)
        self.assertIs(sl.get(0), sub)

    def test_call_custom_args(self):
        results = []
        sl = SubscriptionList()
        sl.append(lambda a, b: results.append((a, b)))
        sl.call_custom_args("x", "y")
        self.assertEqual(results, [("x", "y")])


class TestEventDispatcher(unittest.TestCase):
    """Test cases for the EventDispatcher class."""

    def setUp(self):
        self.ed = EventDispatcher()

    def test_register_event(self):
        self.assertTrue(self.ed._register_event("test-event"))
        self.assertIn("test-event", self.ed.list_events())

    def test_register_duplicate_event(self):
        self.ed._register_event("dup")
        self.assertFalse(self.ed._register_event("dup"))

    def test_register_events_bulk(self):
        self.ed._register_events("a", "b", "c")
        self.assertIn("a", self.ed.events)
        self.assertIn("b", self.ed.events)
        self.assertIn("c", self.ed.events)

    def test_deregister_event(self):
        self.ed._register_event("removable")
        self.assertTrue(self.ed._deregister_event("removable"))
        self.assertNotIn("removable", self.ed.events)

    def test_deregister_nonexistent_event(self):
        self.assertFalse(self.ed._deregister_event("nope"))

    def test_deregister_all_events(self):
        self.ed._register_events("a", "b")
        self.ed._deregister_all_events()
        self.assertEqual(self.ed.events, [])

    def test_dispatch_and_subscribe(self):
        results = []
        self.ed._register_event("click")
        self.ed.subscribe("click", lambda v: results.append(v))
        self.ed._dispatch("click", 99)
        self.assertEqual(results, [99])

    def test_dispatch_nonexistent_event(self):
        self.assertFalse(self.ed._dispatch("missing", 1))

    def test_subscribe_nonexistent_event(self):
        result = self.ed.subscribe("missing", lambda: None)
        self.assertFalse(result)

    def test_subscribe_once(self):
        results = []
        self.ed._register_event("once")
        self.ed.subscribe_once("once", lambda v: results.append(v))
        self.ed._dispatch("once", 1)
        self.ed._dispatch("once", 2)
        self.assertEqual(results, [1])

    def test_unsubscribe(self):
        results = []
        self.ed._register_event("unsub")
        sub = self.ed.subscribe("unsub", lambda v: results.append(v))
        self.ed.unsubscribe("unsub", sub)
        self.ed._dispatch("unsub", 1)
        self.assertEqual(results, [])

    def test_clear_event_subscriptions(self):
        results = []
        self.ed._register_event("evt")
        self.ed.subscribe("evt", lambda v: results.append(v))
        self.ed._clear_event_subscriptions("evt")
        self.ed._dispatch("evt", 1)
        self.assertEqual(results, [])

    def test_event_sub_count(self):
        self.ed._register_event("counted")
        self.assertEqual(self.ed._event_sub_count("counted"), 0)
        self.ed.subscribe("counted", lambda: None)
        self.assertEqual(self.ed._event_sub_count("counted"), 1)

    def test_event_sub_count_nonexistent(self):
        self.assertEqual(self.ed._event_sub_count("nope"), -1)

    def test_subscribe_with_extra_args(self):
        results = []
        self.ed._register_event("args")
        self.ed.subscribe("args", lambda v, tag: results.append((v, tag)), "my_tag")
        self.ed._dispatch("args", 42)
        self.assertEqual(results, [(42, "my_tag")])


class TestSimpleEventDispatcher(unittest.TestCase):
    """Test cases for the SimpleEventDispatcher class."""

    def test_subscribe_and_dispatch(self):
        results = []
        sed = SimpleEventDispatcher()
        sed.subscribe(lambda v: results.append(v))
        sed._dispatch(10)
        self.assertEqual(results, [10])

    def test_multiple_subscribers(self):
        results = []
        sed = SimpleEventDispatcher()
        sed.subscribe(lambda v: results.append(("a", v)))
        sed.subscribe(lambda v: results.append(("b", v)))
        sed._dispatch(5)
        self.assertEqual(results, [("a", 5), ("b", 5)])

    def test_clear_subscriptions(self):
        results = []
        sed = SimpleEventDispatcher()
        sed.subscribe(lambda v: results.append(v))
        sed._clear_subscriptions()
        sed._dispatch(1)
        self.assertEqual(results, [])


class TestObservable(unittest.TestCase):
    """Test cases for the Observable class."""

    def test_initial_value(self):
        obs = Observable(42)
        self.assertEqual(obs.value, 42)

    def test_value_change_dispatches(self):
        results = []
        obs = Observable(0)
        obs.subscribe(lambda v: results.append(v))
        obs.value = 10
        self.assertEqual(results, [10])

    def test_same_value_no_dispatch(self):
        results = []
        obs = Observable(5)
        obs.subscribe(lambda v: results.append(v))
        obs.value = 5
        self.assertEqual(results, [])

    def test_call_dispatches_current_value(self):
        results = []
        obs = Observable(7)
        obs.subscribe(lambda v: results.append(v))
        obs()
        self.assertEqual(results, [7])

    def test_none_initial_value(self):
        obs = Observable()
        self.assertIsNone(obs.value)


class TestBlockingValue(unittest.TestCase):
    """Test cases for the BlockingValue class."""

    def test_set_and_get(self):
        bv = BlockingValue()
        bv.set_value(42)
        self.assertEqual(bv.get_value(timeout=1), 42)

    def test_get_blocks_until_set(self):
        bv = BlockingValue()

        def setter():
            sleep(0.05)
            bv.set_value(99)

        Thread(target=setter, daemon=True).start()
        result = bv.get_value(timeout=2)
        self.assertEqual(result, 99)

    def test_get_timeout_returns_none(self):
        bv = BlockingValue()
        result = bv.get_value(timeout=0.01)
        self.assertIsNone(result)

    def test_get_value_no_clear(self):
        bv = BlockingValue()
        bv.set_value(10)
        val1 = bv.get_value_no_clear(timeout=1)
        val2 = bv.get_value_no_clear(timeout=1)
        self.assertEqual(val1, 10)
        self.assertEqual(val2, 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
