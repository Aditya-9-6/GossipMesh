import unittest
from gossipmesh.p2p.adaptive_fanout import AdaptiveFanoutManager
from gossipmesh.p2p.transport import GossipTransport

class TestAdaptiveFanout(unittest.TestCase):
    def test_default_fanout(self):
        manager = AdaptiveFanoutManager(default_fanout=5)
        self.assertEqual(manager.compute_fanout(), 5)

    def test_high_latency_adaptation(self):
        manager = AdaptiveFanoutManager(default_fanout=5, max_fanout=10)
        for _ in range(10):
            manager.record_metrics(latency_ms=300.0, drop_rate=0.0)
        self.assertGreater(manager.compute_fanout(), 5)

    def test_low_latency_adaptation(self):
        manager = AdaptiveFanoutManager(default_fanout=5, min_fanout=2)
        for _ in range(10):
            manager.record_metrics(latency_ms=50.0, drop_rate=0.0)
        self.assertLess(manager.compute_fanout(), 5)

    def test_transport_integration(self):
        transport = GossipTransport(default_fanout=3, max_fanout=10)
        peers = [f"peer_{i}" for i in range(10)]
        targets = transport.select_gossip_peers(peers)
        self.assertEqual(len(targets), 3)

if __name__ == '__main__':
    unittest.main()
