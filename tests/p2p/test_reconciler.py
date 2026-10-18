import unittest
from gossipmesh.p2p.vector_clock import VectorClock
from gossipmesh.p2p.reconciler import MerkleTree, VectorClockReconciler

class TestVectorClockAndReconciler(unittest.TestCase):
    def test_vector_clock_operations(self):
        vc1 = VectorClock({"node_a": 1})
        vc2 = VectorClock({"node_a": 2})
        
        self.assertEqual(vc1.compare(vc2), 'before')
        self.assertEqual(vc2.compare(vc1), 'after')
        
        vc1.increment("node_a")
        self.assertEqual(vc1.compare(vc2), 'equal')
        
        vc3 = VectorClock({"node_b": 1})
        self.assertEqual(vc1.compare(vc3), 'concurrent')

    def test_merkle_tree_diff(self):
        data1 = {"k1": "v1", "k2": "v2"}
        data2 = {"k1": "v1", "k2": "v_modified", "k3": "v3"}
        
        t1 = MerkleTree(data1)
        t2 = MerkleTree(data2)
        
        self.assertNotEqual(t1.root_hash, t2.root_hash)
        diffs = t1.get_diff(t2)
        self.assertIn("k2", diffs)
        self.assertIn("k3", diffs)
        self.assertNotIn("k1", diffs)

    def test_reconciler_anti_entropy(self):
        vc_a = VectorClock({"node_a": 1})
        state_a = {"item1": "val1", "item2": "val2"}
        reconciler_a = VectorClockReconciler("node_a", state_a, vc_a)

        vc_b = VectorClock({"node_a": 1, "node_b": 1})
        state_b = {"item1": "val1", "item2": "val2_updated"}
        
        digest_vc, digest_root = reconciler_a.generate_digest()
        
        diffs = reconciler_a.reconcile(digest_vc, digest_root, state_b)
        self.assertEqual(diffs, ["item2"])

if __name__ == '__main__':
    unittest.main()
