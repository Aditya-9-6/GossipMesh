import unittest
from gossipmesh.p2p.metrics import EMALatencyTracker, PeerMetricsRegistry
from gossipmesh.p2p.selector import PeerSelector


class TestP2PSelectorAndMetrics(unittest.TestCase):
    def test_ema_tracker_normal_operation(self):
        tracker = EMALatencyTracker(window_size=5, alpha=0.5)
        ema1 = tracker.record(100.0)
        self.assertEqual(ema1, 100.0)
        ema2 = tracker.record(200.0)
        # 0.5 * 200 + 0.5 * 100 = 150
        self.assertEqual(ema2, 150.0)

    def test_ema_tracker_bounded_memory(self):
        tracker = EMALatencyTracker(window_size=3, alpha=0.2)
        tracker.record(10.0)
        tracker.record(20.0)
        tracker.record(30.0)
        tracker.record(40.0)
        self.assertEqual(len(tracker.latencies), 3)
        self.assertIn(40.0, tracker.latencies)
        self.assertNotIn(10.0, tracker.latencies)

    def test_ema_tracker_negative_latency_error(self):
        tracker = EMALatencyTracker()
        with self.assertRaises(ValueError):
            tracker.record(-5.0)

    def test_peer_selector_prioritization(self):
        registry = PeerMetricsRegistry()
        registry.record_latency("peer_slow", 500.0)
        registry.record_latency("peer_fast", 10.0)
        registry.record_latency("peer_medium", 100.0)

        selector = PeerSelector(registry)
        peers = ["peer_slow", "peer_fast", "peer_medium", "peer_unseen"]

        # Force strict exploitation by setting exploration_ratio=0.0
        selected = selector.select_peers(peers, count=2, strategy="hybrid", exploration_ratio=0.0)
        self.assertIn("peer_fast", selected)
        self.assertIn("peer_medium", selected)

    def test_peer_selector_empty_and_edge_cases(self):
        registry = PeerMetricsRegistry()
        selector = PeerSelector(registry)
        self.assertEqual(selector.select_peers([], 3), [])
        self.assertEqual(selector.select_peers(["p1", "p2"], 5), ["p1", "p2"])


if __name__ == "__main__":
    unittest.main()
