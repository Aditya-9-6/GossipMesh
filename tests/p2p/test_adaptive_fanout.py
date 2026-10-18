import unittest
import time
from gossipmesh.p2p.metrics import PeerMetricsTracker
from gossipmesh.p2p.transport import AdaptiveTransport

class TestAdaptiveFanout(unittest.TestCase):
    def setUp(self):
        self.tracker = PeerMetricsTracker(stale_threshold_sec=1.0)
        self.transport = AdaptiveTransport(base_fanout=4, min_fanout=1, max_fanout=10, stale_threshold=1.0)

    def test_record_and_get_rtt(self):
        self.tracker.record_rtt("peer_a", 0.05)
        self.assertEqual(self.tracker.get_rtt("peer_a"), 0.05)
        self.assertEqual(self.tracker.get_rtt("non_existent"), 0.0)

    def test_stale_metrics_expiration(self):
        self.tracker.record_rtt("peer_b", 0.02)
        self.assertEqual(self.tracker.get_rtt("peer_b"), 0.02)
        time.sleep(1.1)
        self.assertEqual(self.tracker.get_rtt("peer_b"), 0.0)

    def test_calculate_fanout_boundaries(self):
        # Without telemetry, returns base fanout
        self.assertEqual(self.transport.calculate_fanout("peer_x"), 4)
        
        # High RTT reduces fanout towards min_fanout
        self.transport.metrics.record_rtt("peer_y", 2.0)
        fanout = self.transport.calculate_fanout("peer_y")
        self.assertGreaterEqual(fanout, self.transport.min_fanout)
        self.assertLessEqual(fanout, self.transport.max_fanout)

    def test_select_peers(self):
        peers = ["peer_1", "peer_2", "peer_3", "peer_4", "peer_5"]
        self.transport.metrics.record_rtt("peer_2", 0.01)
        self.transport.metrics.record_rtt("peer_1", 0.50)
        selected = self.transport.select_peers(peers)
        self.assertLessEqual(len(selected), 4)
        self.assertIn("peer_2", selected)

if __name__ == "__main__":
    unittest.main()
