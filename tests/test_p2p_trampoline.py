import unittest
import time
from gossipmesh.p2p.trampoline import PeerConnectionTrampoline


class TestPeerConnectionTrampoline(unittest.TestCase):
    def setUp(self) -> None:
        self.trampoline = PeerConnectionTrampoline(base_delay=0.05, max_delay=1.0, multiplier=2.0, jitter=0.0)

    def test_initial_state(self) -> None:
        peer_id = "peer-1"
        self.assertEqual(self.trampoline.get_state(peer_id), "idle")
        self.assertTrue(self.trampoline.can_dial(peer_id))

    def test_successful_dial(self) -> None:
        peer_id = "peer-2"
        self.trampoline.set_state(peer_id, "dialing")
        self.assertFalse(self.trampoline.can_dial(peer_id))

        delay = self.trampoline.record_attempt(peer_id, success=True)
        self.assertEqual(delay, 0.0)
        self.assertEqual(self.trampoline.get_state(peer_id), "connected")
        self.assertFalse(self.trampoline.can_dial(peer_id))

    def test_failed_dial_backoff(self) -> None:
        peer_id = "peer-3"
        now = time.time()

        # First failure
        delay1 = self.trampoline.record_attempt(peer_id, success=False, current_time=now)
        self.assertGreater(delay1, 0)
        self.assertEqual(self.trampoline.get_state(peer_id), "backed_off")

        # Cannot dial immediately
        self.assertFalse(self.trampoline.can_dial(peer_id, current_time=now))

        # Can dial after backoff expires
        future = now + delay1 + 0.01
        self.assertTrue(self.trampoline.can_dial(peer_id, current_time=future))

    def test_reset(self) -> None:
        peer_id = "peer-4"
        self.trampoline.record_attempt(peer_id, success=False)
        self.trampoline.reset(peer_id)
        self.assertEqual(self.trampoline.get_state(peer_id), "idle")
        self.assertTrue(self.trampoline.can_dial(peer_id))

    def test_metrics(self) -> None:
        self.trampoline.record_attempt("peer-A", success=True)
        metrics = self.trampoline.get_metrics()
        self.assertEqual(metrics["tracked_peers"], 1)
        self.assertIn("peer-A", metrics["states"])


if __name__ == "__main__":
    unittest.main()
