import unittest
<<<<<<< HEAD
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

if __name__ == '__main__':
=======
from gossipmesh.p2p.matrix import EpidemicReachabilityMatrix
from gossipmesh.p2p.fanout import DynamicFanoutController

class TestEpidemicReachabilityAndFanout(unittest.TestCase):
    def test_reachability_matrix_basic(self):
        matrix = EpidemicReachabilityMatrix("node-1")
        self.assertEqual(matrix.get_reachability("peer-A"), 0.5)
        matrix.record_ack("peer-A", True)
        self.assertGreater(matrix.get_reachability("peer-A"), 0.5)
        matrix.record_ack("peer-A", False)
        self.assertIsInstance(matrix.average_reachability(), float)

    def test_dynamic_fanout_bounds(self):
        controller = DynamicFanoutController("node-1", base_fanout=4, min_fanout=2, max_fanout=8)
        fanout = controller.compute_fanout()
        self.assertGreaterEqual(fanout, 2)
        self.assertLessEqual(fanout, 8)

    def test_fanout_adjustment_feedback(self):
        controller = DynamicFanoutController("node-1", base_fanout=4)
        for _ in range(5):
            controller.update_peer_feedback("peer-A", False)
        low_reach_fanout = controller.compute_fanout()
        self.assertGreaterEqual(low_reach_fanout, 4)

    def test_metrics_export(self):
        controller = DynamicFanoutController("node-1")
        metrics = controller.get_metrics()
        self.assertIn("current_fanout", metrics)
        self.assertIn("matrix", metrics)

if __name__ == "__main__":
>>>>>>> origin/main
    unittest.main()
