import unittest
from gossipmesh.p2p.digest import BloomFilterDigest
from gossipmesh.p2p.sync import AntiEntropySync

class TestBloomFilterDigest(unittest.TestCase):
    def test_bloom_filter_basic_operations(self):
        bf = BloomFilterDigest(capacity=100, error_rate=0.01)
        bf.add("key_1")
        bf.add("key_2")

        self.assertIn("key_1", bf)
        self.assertIn("key_2", bf)
        self.assertNotIn("key_nonexistent", bf)

    def test_serialization_roundtrip(self):
        bf = BloomFilterDigest(capacity=50, error_rate=0.05)
        bf.add("agent_a")
        bf.add("agent_b")

        serialized = bf.serialize()
        deserialized = BloomFilterDigest.deserialize(serialized)

        self.assertEqual(bf.capacity, deserialized.capacity)
        self.assertEqual(bf.error_rate, deserialized.error_rate)
        self.assertEqual(bf.element_count, deserialized.element_count)
        self.assertIn("agent_a", deserialized)
        self.assertIn("agent_b", deserialized)
        self.assertNotIn("agent_c", deserialized)

    def test_anti_entropy_sync_reconciliation(self):
        local_keys = {"item_1", "item_2", "item_3", "item_4"}
        remote_keys = {"item_1", "item_2"}

        digest_data = AntiEntropySync.create_node_digest(remote_keys, capacity=10, error_rate=0.01)
        missing = AntiEntropySync.reconcile(local_keys, digest_data)

        # Local has item_3 and item_4 which remote doesn't have
        self.assertIn("item_3", missing)
        self.assertIn("item_4", missing)
        self.assertNotIn("item_1", missing)
        self.assertNotIn("item_2", missing)

if __name__ == "__main__":
    unittest.main()
