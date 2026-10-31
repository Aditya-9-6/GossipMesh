import unittest
from gossipmesh.p2p.liveness import PeerLivenessTracker, LivenessConfig, SlidingWindowEWMA
from gossipmesh.p2p.node import PeerNode, PeerManager

class TestP2PLiveness(unittest.TestCase):
    def test_sliding_window_ewma(self):
        ewma = SlidingWindowEWMA(capacity=3, alpha=0.5)
        self.assertEqual(ewma.add_sample(10.0), 10.0)
        self.assertEqual(ewma.add_sample(20.0), 15.0)  # 0.5*20 + 0.5*10
        self.assertEqual(ewma.add_sample(30.0), 22.5)  # 0.5*30 + 0.5*15
        samples = ewma.get_samples()
        self.assertEqual(samples, [10.0, 20.0, 30.0])
        
        # Test window capacity rolling
        ewma.add_sample(40.0)
        self.assertEqual(ewma.get_samples(), [20.0, 30.0, 40.0])

    def test_peer_liveness_tracker_happy_path(self):
        config = LivenessConfig(window_size=5, ewma_alpha=0.4, timeout_threshold_ms=500.0, quarantine_failure_count=3)
        tracker = PeerLivenessTracker(config)
        
        res1 = tracker.record_ping("peer-1", 100.0)
        self.assertFalse(res1["is_quarantined"])
        self.assertEqual(res1["consecutive_failures"], 0)
        self.assertEqual(res1["ewma_latency_ms"], 100.0)
        
        res2 = tracker.record_ping("peer-1", 200.0)
        self.assertFalse(res2["is_quarantined"])
        self.assertEqual(res2["consecutive_failures"], 0)
        self.assertAlmostEqual(res2["ewma_latency_ms"], 140.0)

    def test_peer_liveness_quarantine_isolation(self):
        config = LivenessConfig(quarantine_failure_count=2, timeout_threshold_ms=500.0)
        tracker = PeerLivenessTracker(config)
        
        # 1st failure
        r1 = tracker.record_ping("peer-silent", None, timed_out=True)
        self.assertFalse(r1["is_quarantined"])
        self.assertEqual(r1["consecutive_failures"], 1)
        
        # 2nd failure triggers quarantine
        r2 = tracker.record_ping("peer-silent", 600.0, timed_out=False)
        self.assertTrue(r2["is_quarantined"])
        self.assertEqual(r2["consecutive_failures"], 2)
        self.assertTrue(tracker.is_peer_quarantined("peer-silent"))
        
        # Recovery on successful ping
        r3 = tracker.record_ping("peer-silent", 50.0, timed_out=False)
        self.assertFalse(r3["is_quarantined"])
        self.assertEqual(r3["consecutive_failures"], 0)

    def test_peer_node_and_manager_integration(self):
        manager = PeerManager()
        node = manager.add_peer("peer-alpha", "127.0.0.1:8001")
        self.assertTrue(node.is_healthy())
        
        node.record_heartbeat_ping(120.0)
        status = node.get_status()
        self.assertEqual(status["peer_id"], "peer-alpha")
        self.assertIn("liveness", status)
        self.assertEqual(status["liveness"]["ewma_latency_ms"], 120.0)
        
        # Force quarantine via consecutive timeouts
        node.record_heartbeat_ping(None, timed_out=True)
        node.record_heartbeat_ping(None, timed_out=True)
        node.record_heartbeat_ping(None, timed_out=True)
        
        self.assertFalse(node.is_healthy())
        self.assertNotIn("peer-alpha", manager.get_active_peers())

if __name__ == "__main__":
    unittest.main()
