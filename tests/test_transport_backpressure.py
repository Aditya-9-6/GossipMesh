import unittest
from gossipmesh.p2p.metrics import PeerMetricsTracker
from gossipmesh.p2p.transport import calculate_adaptive_fanout, AdaptiveGossipTransport

class TestTransportBackpressure(unittest.TestCase):
    def test_metrics_tracker_smoothing(self):
        tracker = PeerMetricsTracker(alpha=0.5)
        rtt1 = tracker.update_rtt("peer1", 0.1)
        self.assertEqual(rtt1, 0.1)
        rtt2 = tracker.update_rtt("peer1", 0.3)
        self.assertEqual(rtt2, 0.2)

    def test_calculate_adaptive_fanout_normal(self):
        fanout = calculate_adaptive_fanout(base_fanout=8, queue_depth=10, rtt=0.05)
        self.assertEqual(fanout, 8)

    def test_calculate_adaptive_fanout_congested_queue(self):
        fanout = calculate_adaptive_fanout(base_fanout=8, queue_depth=60, rtt=0.05)
        self.assertTrue(fanout < 8)
        self.assertGreaterEqual(fanout, 1)

    def test_calculate_adaptive_fanout_high_rtt(self):
        fanout = calculate_adaptive_fanout(base_fanout=10, queue_depth=5, rtt=0.5)
        self.assertTrue(fanout < 10)
        self.assertGreaterEqual(fanout, 1)

    def test_adaptive_gossip_transport_integration(self):
        transport = AdaptiveGossipTransport(base_fanout=8)
        transport.register_peer("peer_alpha")
        transport.record_peer_telemetry("peer_alpha", queue_depth=100, rtt=0.6)
        fanout = transport.get_effective_fanout("peer_alpha")
        self.assertEqual(fanout, 4)

if __name__ == "__main__":
    unittest.main()
