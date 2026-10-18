import unittest
from gossipmesh.p2p.entropy import VectorClockEntropy
from gossipmesh.p2p.syncer import AntiEntropySyncer

class TestVectorClockEntropy(unittest.TestCase):
    def setUp(self):
        self.entropy = VectorClockEntropy(window_size=10)

    def test_zero_divergence(self):
        clock = {"node1": 5, "node2": 3}
        score = self.entropy.calculate_divergence(clock, clock)
        self.assertEqual(score, 0.0)

    def test_high_divergence(self):
        local = {"node1": 10}
        peer = {"node2": 20}
        score = self.entropy.calculate_divergence(local, peer)
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_select_best_peers(self):
        local = {"node1": 5}
        peers = {
            "peerA": {"node1": 5},     # 0 divergence
            "peerB": {"node1": 15},    # medium divergence
            "peerC": {"node1": 105}
        }
        selected = self.entropy.select_best_peers(local, peers, top_k=2)
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0][0], "peerC")

    def test_sliding_window_memory_bound(self):
        local = {"node1": 1}
        for i in range(20):
            peer = {"node1": i + 2}
            self.entropy.calculate_divergence(local, peer)
        self.assertEqual(len(self.entropy.history), 10)

    def test_syncer_integration(self):
        syncer = AntiEntropySyncer(node_id="node1", window_size=5)
        local = {"node1": 10}
        peers = {
            "p1": {"node1": 10},
            "p2": {"node1": 50}
        }
        best = syncer.select_sync_peers(local, peers, limit=1)
        self.assertEqual(len(best), 1)
        self.assertEqual(best[0][0], "p2")

if __name__ == "__main__":
    unittest.main()
