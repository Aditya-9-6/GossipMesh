import unittest
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
    unittest.main()
