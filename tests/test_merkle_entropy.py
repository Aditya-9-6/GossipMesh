import unittest
from gossipmesh.p2p.merkle import MerkleTree
from gossipmesh.p2p.entropy import AntiEntropyEngine


class TestMerkleAndEntropy(unittest.TestCase):
    def test_merkle_tree_identical(self):
        data = {"a": "1", "b": "2", "c": "3"}
        tree1 = MerkleTree(data)
        tree2 = MerkleTree(data)
        self.assertEqual(tree1.get_root_hash(), tree2.get_root_hash())

    def test_merkle_tree_different(self):
        data1 = {"a": "1", "b": "2"}
        data2 = {"a": "1", "b": "3"}
        tree1 = MerkleTree(data1)
        tree2 = MerkleTree(data2)
        self.assertNotEqual(tree1.get_root_hash(), tree2.get_root_hash())

    def test_anti_entropy_reconciliation(self):
        engine1 = AntiEntropyEngine("node-1")
        engine1.set_state("k1", "v1")
        engine1.set_state("k2", "v2")

        engine2 = AntiEntropyEngine("node-2")
        engine2.set_state("k1", "v1")
        engine2.set_state("k2", "v-modified")

        diffs = engine1.reconcile_divergence(engine2.state_store)
        self.assertIn("k2", diffs)


if __name__ == "__main__":
    unittest.main()
