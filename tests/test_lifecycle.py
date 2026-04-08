"""Tests for connection lifecycle state machine."""

import unittest

from src.lifecycle import ConnectionState, LifecycleManager


class TestLifecycleTransitions(unittest.TestCase):
    def test_initial_state_is_disconnected(self) -> None:
        lm = LifecycleManager()
        self.assertEqual(lm.state, ConnectionState.DISCONNECTED)
        self.assertFalse(lm.is_ready)

    def test_happy_path_to_ready(self) -> None:
        lm = LifecycleManager()
        lm.transition_to(ConnectionState.CONNECTING, "pipe", "opening")
        lm.transition_to(ConnectionState.HANDSHAKE, "pipe", "data received")
        lm.transition_to(ConnectionState.READY, "pipe", "response ok")
        self.assertTrue(lm.is_ready)
        self.assertEqual(lm.transport, "pipe")
        self.assertEqual(lm.ready_count, 1)

    def test_invalid_transition_raises(self) -> None:
        lm = LifecycleManager()
        with self.assertRaises(ValueError):
            lm.transition_to(ConnectionState.READY)  # Can't jump from DISCONNECTED

    def test_error_from_connecting(self) -> None:
        lm = LifecycleManager()
        lm.transition_to(ConnectionState.CONNECTING, "pipe")
        lm.transition_to(ConnectionState.ERROR, detail="pipe not found")
        self.assertEqual(lm.state, ConnectionState.ERROR)
        self.assertEqual(lm.error_count, 1)

    def test_reconnect_after_error(self) -> None:
        lm = LifecycleManager()
        lm.transition_to(ConnectionState.CONNECTING, "pipe")
        lm.transition_to(ConnectionState.ERROR, detail="broken")
        lm.transition_to(ConnectionState.CONNECTING, "tcp", "fallback to tcp")
        lm.transition_to(ConnectionState.HANDSHAKE, "tcp")
        lm.transition_to(ConnectionState.READY, "tcp")
        self.assertTrue(lm.is_ready)
        self.assertEqual(lm.transport, "tcp")
        self.assertEqual(lm.error_count, 1)
        self.assertEqual(lm.ready_count, 1)


class TestLifecycleHistory(unittest.TestCase):
    def test_history_records_transitions(self) -> None:
        lm = LifecycleManager()
        lm.transition_to(ConnectionState.CONNECTING, "pipe")
        lm.transition_to(ConnectionState.HANDSHAKE, "pipe")
        self.assertEqual(len(lm.history), 2)
        self.assertEqual(lm.history[0].to_state, ConnectionState.CONNECTING)
        self.assertEqual(lm.history[1].to_state, ConnectionState.HANDSHAKE)

    def test_history_capped_at_max(self) -> None:
        lm = LifecycleManager()
        lm._MAX_HISTORY = 5
        # Cycle through states many times
        for _ in range(10):
            lm.transition_to(ConnectionState.CONNECTING, "pipe")
            lm.transition_to(ConnectionState.ERROR, detail="test")
        self.assertLessEqual(len(lm.history), 5)


class TestLifecycleCallbacks(unittest.TestCase):
    def test_callback_invoked_on_transition(self) -> None:
        events: list[object] = []
        lm = LifecycleManager()
        lm.on_state_change(lambda e: events.append(e))
        lm.transition_to(ConnectionState.CONNECTING, "pipe")
        self.assertEqual(len(events), 1)

    def test_broken_callback_does_not_crash(self) -> None:
        lm = LifecycleManager()
        lm.on_state_change(lambda e: 1 / 0)  # will raise
        # Should not raise
        lm.transition_to(ConnectionState.CONNECTING, "pipe")
        self.assertEqual(lm.state, ConnectionState.CONNECTING)


class TestLifecycleDiagnostics(unittest.TestCase):
    def test_to_dict_snapshot(self) -> None:
        lm = LifecycleManager()
        lm.transition_to(ConnectionState.CONNECTING, "pipe")
        lm.transition_to(ConnectionState.ERROR, detail="timeout")
        d = lm.to_dict()
        self.assertEqual(d["state"], "error")
        self.assertEqual(d["transport"], "pipe")
        self.assertEqual(d["errorCount"], 1)
        self.assertEqual(d["lastError"], "timeout")

    def test_reset_returns_to_disconnected(self) -> None:
        lm = LifecycleManager()
        lm.transition_to(ConnectionState.CONNECTING, "pipe")
        lm.transition_to(ConnectionState.HANDSHAKE, "pipe")
        lm.transition_to(ConnectionState.READY, "pipe")
        lm.reset()
        self.assertEqual(lm.state, ConnectionState.DISCONNECTED)


if __name__ == "__main__":
    unittest.main()
