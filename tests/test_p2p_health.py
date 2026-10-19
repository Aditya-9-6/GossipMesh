import unittest
from gossipmesh.p2p.health import SlidingWindowPeerHealthScorecard, PeerHealthConfig
from gossipmesh.p2p.peer import PeerManager, PeerNode

class TestPeerHealthScorecard(unittest.TestCase):
    def test_initial_state(self):
        scorecard = SlidingWindowPeerHealthScorecard()
        metrics = scorecard.get_metrics()
        self.assertEqual(metrics["health_score"], 100.0)
        self.assertFalse(metrics["is_quarantined"])
        self.assertEqual(metrics["total_samples"], 0)

    def test_normal_operation_samples(self):
        config = PeerHealthConfig(quarantine_threshold=30.0, recovery_threshold=70.0)
        scorecard = SlidingWindowPeerHealthScorecard(config)
        
        score = scorecard.record_sample(latency_ms=15.0, dropped=False, violated=False)
        self.assertGreater(score, 80.0)
        self.assertFalse(scorecard.get_metrics()["is_quarantined"])

    def test_quarantine_and_recovery(self):
        config = PeerHealthConfig(quarantine_threshold=50.0, recovery_threshold=80.0)
        scorecard = SlidingWindowPeerHealthScorecard(config)

        # Induce severe degradation and violations
        for _ in range(10):
            score = scorecard.record_sample(latency_ms=800.0, dropped=True, violated=True)
            
        metrics = scorecard.get_metrics()
        self.assertTrue(metrics["is_quarantined"])
        self.assertLessEqual(metrics["health_score"], 50.0)

        # Recover node with pristine samples
        for _ in range(15):
            score = scorecard.record_sample(latency_ms=5.0, dropped=False, violated=False)
            
        metrics_after = scorecard.get_metrics()
        self.assertFalse(metrics_after["is_quarantined"])
        self.assertGreaterEqual(metrics_after["health_score"], 80.0)

    def test_peer_manager_integration(self):
        manager = PeerManager()
        peer = manager.add_peer("node-alpha", "127.0.0.1:8000")
        
        self.assertIn("node-alpha", manager.get_active_peers())
        
        # Degrade peer
        for _ in range(10):
            peer.record_interaction(latency_ms=1000.0, dropped=True, violated=True)
            
        self.assertNotIn("node-alpha", manager.get_active_peers())
        status = peer.get_status()
        self.assertTrue(status["is_quarantined"])

if __name__ == "__main__":
    unittest.main()
