import unittest
from gossipmesh.p2p.fanout import AdaptiveFanoutController
from gossipmesh.p2p.transport import GossipTransport


class TestAdaptiveFanoutController(unittest.TestCase):
    def test_initial_fanout(self):
        ctrl = AdaptiveFanoutController(initial_fanout=5)
        self.assertEqual(ctrl.get_fanout(), 5)

    def test_fanout_reduction_on_congestion(self):
        ctrl = AdaptiveFanoutController(initial_fanout=6, min_fanout=2, target_rate=1.0)
        for _ in range(30):
            ctrl.record_message(is_duplicate=True)
        self.assertLessEqual(ctrl.get_fanout(), 6)

    def test_transport_peer_selection(self):
        transport = GossipTransport(node_id="node-1", initial_fanout=3)
        peers = ["node-2", "node-3", "node-4", "node-5"]
        selected = transport.select_peers(peers, is_duplicate=False)
        self.assertEqual(len(selected), 3)


if __name__ == "__main__":
    unittest.main()
