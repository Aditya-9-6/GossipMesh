import unittest
import time
from gossipmesh.p2p.metrics import PeerMetricsRegistry
from gossipmesh.p2p.transport import AdaptiveTransport

class TestAdaptiveFanout(unittest.TestCase):
    def setUp(self):
        self.registry = PeerMetricsRegistry(ttl_seconds=2.0)
        self.transport = AdaptiveTransport(self.registry, base_fanout=3)

    def test_basic_peer_selection(self):
        peers = ["peer_a", "peer_b", "peer_c", "peer_d", "peer_e"]
        selected = self.transport.select_peers(peers, congestion_signal=0.0)
        self.assertTrue(len(selected) <= 3)
        self.assertTrue(len(selected) > 0)

    def test_latency_aware_pruning(self):
        self.registry.record_rtt("fast_peer", 0.01)
        self.registry.record_rtt("slow_peer", 5.0)
        self.registry.record_rtt("medium_peer", 0.1)

        peers = ["slow_peer", "fast_peer", "medium_peer"]
        selected = self.transport.select_peers(peers, congestion_signal=0.0)
        
        self.assertEqual(selected[0], "fast_peer")

    def test_congestion_scaling(self):
        fanout_normal = self.transport.calculate_fanout(10, congestion_signal=0.0)
        fanout_congested = self.transport.calculate_fanout(10, congestion_signal=0.8)
        self.assertLessEqual(fanout_congested, fanout_normal)

    def test_stale_metrics_expiration(self):
        self.registry.record_rtt("stale_peer", 0.05)
        self.registry.ttl_seconds = -1.0
        smoothed, failures = self.registry.get_metrics("stale_peer")
        self.assertEqual(smoothed, 0.1)

if __name__ == "__main__":
    unittest.main()
