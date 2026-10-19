import unittest
from gossipmesh.p2p.merkle_trie import MerklePatriciaTree

class TestMerklePatriciaTree(unittest.TestCase):
    def test_empty_trie(self):
        trie = MerklePatriciaTree()
        self.assertIsNotNone(trie.get_root_hash())

    def test_insert_and_root(self):
        trie = MerklePatriciaTree()
        trie.insert("agent_1", {"status": "active"})
        h1 = trie.get_root_hash()
        trie.insert("agent_2", {"status": "idle"})
        h2 = trie.get_root_hash()
        self.assertNotEqual(h1, h2)

    def test_delete_node(self):
        trie = MerklePatriciaTree()
        trie.insert("node_a", 100)
        h1 = trie.get_root_hash()
        trie.delete("node_a")
        h2 = trie.get_root_hash()
        self.assertNotEqual(h1, h2)
        self.assertEqual(h2, trie.get_root_hash())

    def test_proof_generation(self):
        trie = MerklePatriciaTree()
        trie.insert("key1", "val1")
        trie.insert("key2", "val2")
        proof = trie.get_proof("key1")
        self.assertIsInstance(proof, list)

if __name__ == '__main__':
    unittest.main()
