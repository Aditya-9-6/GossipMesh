import unittest
from gossipmesh.consensus.merkle import MerkleTree, hash_data
from gossipmesh.consensus.syncer import MerkleSyncer


class TestConsensusMerkleAndSyncer(unittest.TestCase):
    def test_merkle_tree_identical_trees(self):
        items_a = {"key1": "val1", "key2": "val2", "key3": "val3"}
        items_b = {"key1": "val1", "key2": "val2", "key3": "val3"}

        tree_a = MerkleTree(items_a)
        tree_b = MerkleTree(items_b)

        self.assertEqual(tree_a.get_root_hash(), tree_b.get_root_hash())

    def test_merkle_tree_divergent_trees(self):
        items_a = {"key1": "val1", "key2": "val2"}
        items_b = {"key1": "val1", "key2": "val_modified"}

        tree_a = MerkleTree(items_a)
        tree_b = MerkleTree(items_b)

        self.assertNotEqual(tree_a.get_root_hash(), tree_b.get_root_hash())

    def test_syncer_reconciliation(self):
        items_a = {"alpha": "100", "beta": "200", "gamma": "300"}
        items_b = {"alpha": "100", "beta": "999", "delta": "400"}

        tree_a = MerkleTree(items_a)
        tree_b = MerkleTree(items_b)

        syncer_a = MerkleSyncer(tree_a)
        syncer_b = MerkleSyncer(tree_b)

        manifest_b = syncer_b.get_sync_manifest()
        divergent = syncer_a.reconcile(manifest_b)

        # beta, gamma, and delta should be divergent
        self.assertIn("beta", divergent)
        self.assertIn("gamma", divergent)
        self.assertIn("delta", divergent)
        self.assertNotIn("alpha", divergent)

        delta = syncer_a.generate_delta_payload(divergent)
        self.assertIn("beta", delta)
        self.assertEqual(delta["beta"], "200")
        self.assertNotIn("alpha", delta)

    def test_empty_tree(self):
        tree = MerkleTree()
        self.assertEqual(tree.get_root_hash(), hash_data(""))
        syncer = MerkleSyncer(tree)
        self.assertEqual(syncer.get_sync_manifest(), {})


if __name__ == "__main__":
    unittest.main()
