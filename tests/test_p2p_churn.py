import unittest
from gossipmesh.p2p.churn import PeerChurnDefenseEngine, ChurnDefenseConfig
from gossipmesh.p2p.node import PeerNode, PeerManager


class TestPeerChurnDefense(unittest.TestCase):
    def test_shannon_entropy_calculation(self):
        engine = PeerChurnDefenseEngine()
        vector = {"node1": 10, "node2": 10}
        entropy = engine._compute_shannon_entropy(vector)
        self.assertAlmostEqual(entropy, 1.0, places=2)

    def test_empty_vector_entropy(self):
        engine = PeerChurnDefenseEngine()
        self.assertEqual(engine._compute_shannon_entropy({}), 0.0)
        self.assertEqual(engine._compute_shannon_entropy({"a": 0}), 0.0)

    def test_churn_defense_normal_operation(self):
        config = ChurnDefenseConfig(min_samples_for_evaluation=5, entropy_variance_threshold=1.0)
        engine = PeerChurnDefenseEngine(config)
        peer_id = "peer-stable"

        # Feed consistent heartbeat vectors
        for _ in range(10):
            engine.record_heartbeat(peer_id, {"a": 5, "b": 5})

        should_drop, reason = engine.evaluate_peer(peer_id)
        self.assertFalse(should_drop)
        self.assertEqual(reason, "Normal")

    def test_sybil_flooding_detection_and_drop(self):
        config = ChurnDefenseConfig(
            window_size=10,
            min_samples_for_evaluation=5,
            entropy_variance_threshold=0.01,
            max_ticks_to_drop=3
        )
        engine = PeerChurnDefenseEngine(config)
        peer_id = "peer-sybil"

        # Feed wildly fluctuating vectors causing high variance
        fluctuating_vectors = [
            {"a": 100, "b": 1},
            {"a": 1, "b": 100},
            {"a": 50, "b": 50},
            {"a": 2, "b": 200},
            {"a": 99, "b": 5},
        ]

        should_drop = False
        for _ in range(3):  # 3 evaluation ticks exceeding threshold
            for vec in fluctuating_vectors:
                engine.record_heartbeat(peer_id, vec)
            should_drop, reason = engine.evaluate_peer(peer_id)

        self.assertTrue(should_drop)
        self.assertIn("Sybil detected", reason)

    def test_peer_node_integration(self):
        node = PeerNode("peer-1", "127.0.0.1:8000")
        for _ in range(15):
            node.record_heartbeat_vector({"x": 10, "y": 20})
        self.assertTrue(node.is_healthy())

    def test_peer_manager_churn_integration(self):
        manager = PeerManager()
        peer = manager.add_peer("peer-2", "127.0.0.1:8001")
        self.assertIsNotNone(peer)
        self.assertIn("peer-2", manager.get_active_peers())


if __name__ == "__main__":
    unittest.main()
