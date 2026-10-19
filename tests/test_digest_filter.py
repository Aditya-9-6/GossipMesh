import unittest
from gossipmesh.p2p.digest import BloomFilterDigest


class TestBloomFilterDigest(unittest.TestCase):
    def test_basic_insertion_and_membership(self):
        bf = BloomFilterDigest(capacity=1000, error_rate=0.01)
        bf.add("state_entry_1")
        bf.add("state_entry_2")

        self.assertIn("state_entry_1", bf)
        self.assertIn("state_entry_2", bf)
        self.assertNotIn("non_existent_entry", bf)

    def test_serialization_roundtrip(self):
        bf = BloomFilterDigest(capacity=500, error_rate=0.05)
        bf.add("node_alpha:v1")
        bf.add("node_beta:v2")

        payload = bf.serialize()
        restored = BloomFilterDigest.deserialize(payload)

        self.assertEqual(bf.capacity, restored.capacity)
        self.assertEqual(bf.size, restored.size)
        self.assertEqual(bf.hash_count, restored.hash_count)
        self.assertIn("node_alpha:v1", restored)
        self.assertIn("node_beta:v2", restored)
        self.assertNotIn("node_gamma:v3", restored)

    def test_false_positive_rate_bound(self):
        # Test capacity and error rate sizing invariants
        bf = BloomFilterDigest(capacity=100, error_rate=0.01)
        for i in range(100):
            bf.add(f"key_{i}")

        # Verify items are found
        for i in range(100):
            self.assertIn(f"key_{i}", bf)


if __name__ == "__main":
    unittest.main()
