import unittest
from gossipmesh.p2p.health import PeerHealthMonitor, PeerHealthConfig
from gossipmesh.p2p.peer import PeerNode

class TestPeerHealth(unittest.TestCase):
    def test_health_monitor_normal_operation(self):
        monitor = PeerHealthMonitor()
        sc = monitor.record_metric("peer_1", latency=0.05, dropped=False, violated=False)
        self.assertGreater(sc.overall_score, 0.8)
        self.assertFalse(sc.is_quarantined)
        self.assertTrue(monitor.is_peer_healthy("peer_1"))

    def test_health_monitor_quarantine_and_recovery(self):
        config = PeerHealthConfig(quarantine_threshold=0.5, recovery_threshold=0.8)
        monitor = PeerHealthMonitor(config=config)
        
        # Degrade peer performance
        for _ in range(10):
            sc = monitor.record_metric("peer_2", latency=0.9, dropped=True, violated=True)
            
        self.assertTrue(sc.is_quarantined)
        self.assertFalse(monitor.is_peer_healthy("peer_2"))
        
        # Recover peer performance
        for _ in range(15):
            sc = monitor.record_metric("peer_2", latency=0.01, dropped=False, violated=False)
            
        self.assertFalse(sc.is_quarantined)
        self.assertTrue(monitor.is_peer_healthy("peer_2"))

    def test_peer_node_integration(self):
        monitor = PeerHealthMonitor()
        peer = PeerNode("peer_3", "127.0.0.1:8000", health_monitor=monitor)
        self.assertTrue(peer.is_healthy())
        sc = peer.record_interaction(latency=0.5, dropped=False, violated=False)
        self.assertIsNotNone(sc)
        data = peer.to_dict()
        self.assertEqual(data["peer_id"], "peer_3")
        self.assertIn("healthy", data)

if __name__ == "__main":
    unittest.main()
