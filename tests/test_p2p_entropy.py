import unittest
from gossipmesh.p2p.entropy import VectorClockEntropyEngine, MerkleIntervalNode
from gossipmesh.p2p.protocol import EntropyControlFrame

class TestVectorClockEntropyEngine(unittest.TestCase):
    def test_compare_clocks(self):
        c1 = {"node_a": 2, "node_b": 1}
        c2 = {"node_a": 1, "node_b": 1}
        c3 = {"node_a": 2, "node_b": 2}
        c4 = {"node_a": 2, "node_c": 1}

        self.assertEqual(VectorClockEntropyEngine.compare_clocks(c1, c2), "after")
        self.assertEqual(VectorClockEntropyEngine.compare_clocks(c2, c1), "before")
        self.assertEqual(VectorClockEntropyEngine.compare_clocks(c1, c1), "equal")
        self.assertEqual(VectorClockEntropyEngine.compare_clocks(c1, c4), "concurrent")

    def test_merkle_tree_generation(self):
        store = {"key1": "val1", "key2": "val2", "key3": "val3"}
        nodes = VectorClockEntropyEngine.build_merkle_tree(store, bucket_size=2)
        self.assertGreaterEqual(len(nodes), 1)
        self.assertIsInstance(nodes[0], MerkleIntervalNode)

    def test_reconcile_state_concurrent(self):
        local_state = {"k1": "local_val"}
        local_clock = {"node_a": 2}
        peer_state = {"k2": "peer_val"}
        peer_clock = {"node_b": 2}

        merged_state, merged_clock = VectorClockEntropyEngine.reconcile_state(
            local_state, local_clock, peer_state, peer_clock
        )
        self.assertIn("k1", merged_state)
        self.assertIn("k2", merged_state)
        self.assertEqual(merged_clock["node_a"], 2)
        self.assertEqual(merged_clock["node_b"], 2)

    def test_protocol_frame(self):
        frame = EntropyControlFrame(sender_id="node_1", vector_clock={"node_1": 1}, merkle_digest="abc")
        d = frame.to_dict()
        frame2 = EntropyControlFrame.from_dict(d)
        self.assertEqual(frame.sender_id, frame2.sender_id)
        self.assertEqual(frame.merkle_digest, frame2.merkle_digest)

if __name__ == "__main__":
    unittest.main()
