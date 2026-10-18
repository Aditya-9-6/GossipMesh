import unittest
from gossipmesh.p2p.fanout import AdaptiveFanoutController
from gossipmesh.p2p.transport import GossipTransport

class TestAdaptiveFanout(unittest.TestCase):
    def setUp(self):
        self.controller = AdaptiveFanoutController(base_fanout=4, min_fanout=2, max_fanout=16)

    def test_normal_operation(self):
        fanout = self.controller.compute_fanout(network_latency_ms=50.0, peer_churn_rate=0.1, total_peers=10)
        self.assertGreaterEqual(fanout, self.controller.min_fanout)
        self.assertLessEqual(fanout, self.controller.max_fanout)

    def test_boundary_conditions(self):
        # Zero peers edge case
        fanout_zero = self.controller.compute_fanout(network_latency_ms=10.0, peer_churn_rate=0.0, total_peers=0)
        self.assertEqual(fanout_zero, self.controller.min_fanout)

        # Extremely high latency and churn
        fanout_high = self.controller.compute_fanout(network_latency_ms=5000.0, peer_churn_rate=1.0, total_peers=1000)
        self.assertEqual(fanout_high, self.controller.max_fanout)

    def test_transport_integration(self):
        transport = GossipTransport(base_fanout=4)
        transport.peers = [f"peer_{i}" for i in range(20)]
        fanout = transport.get_adaptive_fanout(latency_ms=100.0, churn_rate=0.2)
        self.assertGreaterEqual(fanout, 2)
        self.assertLessEqual(fanout, 16)

if __name__ == '__main__':
    unittest.main()
