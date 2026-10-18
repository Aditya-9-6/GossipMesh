import unittest
from gossipmesh.p2p.merkle import MerkleTree
from gossipmesh.p2p.entropy import AntiEntropyManager


class TestMerkleAndEntropy(unittest.TestCase):
    def test_merkle_identical_trees(self):
        data = {"a": "1", "b": "2", "c": "3"}
        tree1 = MerkleTree(data)
        tree2 = MerkleTree(data)
        self.assertEqual(tree1.get_root_hash(), tree2.get_root_hash())

    def test_merkle_different_trees(self):
        data1 = {"a": "1", "b": "2"}
        data2 = {"a": "1", "b": "3"}
        tree1 = MerkleTree(data1)
        tree2 = MerkleTree(data2)
        self.assertNotEqual(tree1.get_root_hash(), tree2.get_root_hash())
        diffs = tree1.find_divergent_keys(tree2.root)
        self.assertIn("b", diffs)

    def test_anti_entropy_reconciliation(self):
        manager1 = AntiEntropyManager("node-1")
        manager2 = AntiEntropyManager("node-2")

        manager1.set_state("k1", "v1")
        manager1.set_state("k2", "v2")

        manager2.set_state("k1", "v1")
        manager2.set_state("k2", "v_modified")

        tree2 = manager2.get_merkle_tree()
        diffs = manager1.reconcile_state("node-2", tree2)
        self.assertEqual(diffs, ["k2"])

    def test_empty_trees(self):
        tree1 = MerkleTree({})
        tree2 = MerkleTree({})
        self.assertIsNone(tree1.get_root_hash())
        self.assertEqual(tree1.find_divergent_keys(tree2.root), [])


if __name__ == "__main__":
    unittest.main()
