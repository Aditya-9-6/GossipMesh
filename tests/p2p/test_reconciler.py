import unittest
from gossipmesh.p2p.vector_clock import VectorClock
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
    unittest.main()
