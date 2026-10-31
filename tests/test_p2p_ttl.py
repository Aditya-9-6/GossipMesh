"""Unit tests for adaptive epidemic TTL decay and congestion-aware poison-reverse."""

import unittest
from gossipmesh.p2p.ttl import AdaptiveTTLManager, TTLConfig


class TestAdaptiveTTLManager(unittest.TestCase):
    def setUp(self):
        self.config = TTLConfig(
            base_ttl=10,
            min_ttl=1,
            queue_congestion_threshold=100,
            latency_congestion_threshold_sec=0.1,
            decay_penalty=2,
            poison_reverse_penalty=3,
        )
        self.manager = AdaptiveTTLManager(self.config)

    def test_normal_ttl_decay(self):
        # Normal conditions: queue depth low, no peer latency
        decayed = self.manager.calculate_decayed_ttl(10, 10, None)
        self.assertEqual(decayed, 9)  # standard penalty = 1

    def test_queue_congestion_decay(self):
        # Queue depth >= 100 triggers decay_penalty (2) + standard (1) = 3
        decayed = self.manager.calculate_decayed_ttl(10, 150, None)
        self.assertEqual(decayed, 7)

    def test_poison_reverse_latency_decay(self):
        self.manager.update_peer_latency("peer-slow", 0.15)
        # queue depth low, but slow peer triggers poison_reverse_penalty (3) + standard (1) = 4
        decayed = self.manager.calculate_decayed_ttl(10, 10, "peer-slow")
        self.assertEqual(decayed, 6)

    def test_combined_congestion_and_poison_reverse(self):
        self.manager.update_peer_latency("peer-congested", 0.2)
        # queue penalty (2) + poison reverse penalty (3) + standard (1) = 6
        decayed = self.manager.calculate_decayed_ttl(10, 200, "peer-congested")
        self.assertEqual(decayed, 4)

    def test_should_drop(self):
        self.assertTrue(self.manager.should_drop(1, 10, None))
        self.assertFalse(self.manager.should_drop(5, 10, None))

    def test_validation_errors(self):
        with self.assertRaises(ValueError):
            self.manager.update_peer_latency("", 0.05)
        with self.assertRaises(ValueError):
            self.manager.update_peer_latency("peer-1", -0.1)

    def test_reset_and_get_latency(self):
        self.manager.update_peer_latency("peer-1", 0.05)
        self.assertEqual(self.manager.get_peer_latency("peer-1"), 0.05)
        self.manager.reset()
        self.assertIsNone(self.manager.get_peer_latency("peer-1"))


if __name__ == "__main__":
    unittest.main()
