import unittest
import time
from gossipmesh.p2p.liveness import PeerLivenessTracker

class TestPeerLivenessTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = PeerLivenessTracker(window_size=5, alpha=0.3, max_ttl_ms=1000.0)

    def test_ping_pong_latency_recording(self):
        peer_id = "peer-node-1"
        self.tracker.record_ping_sent(peer_id)
        time.sleep(0.01)
        rtt = self.tracker.record_pong_received(peer_id)
        
        self.assertIsNotNone(rtt)
        self.assertGreater(rtt, 0.0)
        self.assertGreater(self.tracker.get_ewma_latency(peer_id), 0.0)

    def test_health_score_boundary_conditions(self):
        peer_id = "peer-node-2"
        # Unseen peer should have 0 health
        self.assertEqual(self.tracker.get_health_score(peer_id), 0.0)
        self.assertFalse(self.tracker.is_healthy(peer_id))
        
        # Record ping/pong
        self.tracker.record_ping_sent(peer_id)
        self.tracker.record_pong_received(peer_id)
        
        score = self.tracker.get_health_score(peer_id)
        self.assertGreater(score, 0.0)
        self.assertTrue(self.tracker.is_healthy(peer_id))

    def test_expired_peer_partition_isolation(self):
        peer_id = "silent-peer"
        self.tracker.record_ping_sent(peer_id)
        self.tracker.record_pong_received(peer_id)
        
        # Simulate expiration by manipulating last_seen
        with self.tracker._lock:
            self.tracker._last_seen[peer_id] = (time.time() * 1000.0) - 2000.0
            
        self.assertEqual(self.tracker.get_health_score(peer_id), 0.0)
        self.assertFalse(self.tracker.is_healthy(peer_id))
        self.assertNotIn(peer_id, self.tracker.get_active_peers())

if __name__ == "__main__":
    unittest.main()
