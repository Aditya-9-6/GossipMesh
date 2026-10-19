import unittest
from gossipmesh.p2p.vector_clock import VectorClock
<<<<<<< HEAD
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
=======
from gossipmesh.p2p.reconciler import MerkleTree, AntiEntropyReconciler

class TestVectorClock(unittest.TestCase):
    def test_vector_clock_operations(self):
        vc1 = VectorClock({"nodeA": 1})
        vc2 = VectorClock({"nodeA": 2})
        self.assertEqual(vc1.compare(vc2), "BEFORE")
        self.assertEqual(vc2.compare(vc1), "AFTER")
        
        vc3 = VectorClock({"nodeA": 1, "nodeB": 1})
        vc4 = VectorClock({"nodeA": 1, "nodeB": 2})
        self.assertEqual(vc3.compare(vc4), "BEFORE")
        
        vc5 = VectorClock({"nodeA": 2, "nodeB": 1})
        vc6 = VectorClock({"nodeA": 1, "nodeB": 2})
        self.assertEqual(vc5.compare(vc6), "CONCURRENT")

class TestMerkleTreeAndReconciler(unittest.TestCase):
    def test_merkle_tree_hashing(self):
        data1 = {"a": "1", "b": "2"}
        data2 = {"a": "1", "b": "2"}
        data3 = {"a": "1", "b": "3"}

        tree1 = MerkleTree(data1)
        tree2 = MerkleTree(data2)
        tree3 = MerkleTree(data3)

        self.assertEqual(tree1.get_root_hash(), tree2.get_root_hash())
        self.assertNotEqual(tree1.get_root_hash(), tree3.get_root_hash())

    def test_reconciler_workflow(self):
        rec1 = AntiEntropyReconciler("node1")
        rec2 = AntiEntropyReconciler("node2")

        rec1.set_state("key1", "val1")
        tree1 = rec1.get_merkle_tree()

        action = rec2.reconcile("node1", rec1.vector_clock.to_dict(), tree1.get_root_hash())
        self.assertEqual(action, "PULL_FROM_PEER")

        rec2.set_state("key1", "val1")
        rec1.set_state("key2", "val2")
        rec2.set_state("key2", "val3")

        action2 = rec1.reconcile("node2", rec2.vector_clock.to_dict(), rec2.get_merkle_tree().get_root_hash())
        self.assertEqual(action2, "EXCHANGE_MERKLE")

        diffs = rec1.find_differences(rec2.store)
        self.assertIn("key2", diffs)

if __name__ == "__main__":
>>>>>>> origin/main
    unittest.main()
