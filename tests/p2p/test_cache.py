import time
import unittest
from gossipmesh.p2p.cache import GossipMessageCache


class TestGossipMessageCache(unittest.TestCase):
    def setUp(self):
        self.cache = GossipMessageCache(capacity=3, default_ttl=1.0)

    def test_put_and_get(self):
        self.cache.put("msg-1", "payload-1")
        self.assertTrue(self.cache.has("msg-1"))
        self.assertEqual(self.cache.get("msg-1"), "payload-1")
        self.assertIn("msg-1", self.cache)

    def test_lru_eviction(self):
        self.cache.put("msg-1", "p1")
        self.cache.put("msg-2", "p2")
        self.cache.put("msg-3", "p3")

        # Access msg-1 to make it recently used
        self.assertEqual(self.cache.get("msg-1"), "p1")

        # Adding msg-4 should evict msg-2 (least recently used)
        self.cache.put("msg-4", "p4")

        self.assertTrue(self.cache.has("msg-1"))
        self.assertFalse(self.cache.has("msg-2"))
        self.assertTrue(self.cache.has("msg-3"))
        self.assertTrue(self.cache.has("msg-4"))
        self.assertEqual(len(self.cache), 3)

    def test_ttl_expiration(self):
        self.cache.put("msg-ttl", "data", ttl=0.2)
        self.assertTrue(self.cache.has("msg-ttl"))

        # Wait for TTL to expire
        time.sleep(0.3)
        self.assertFalse(self.cache.has("msg-ttl"))
        self.assertIsNone(self.cache.get("msg-ttl"))
        self.assertEqual(len(self.cache), 0)

    def test_clear(self):
        self.cache.put("msg-1", "p1")
        self.cache.put("msg-2", "p2")
        self.assertEqual(len(self.cache), 2)
        self.cache.clear()
        self.assertEqual(len(self.cache), 0)
        self.assertFalse(self.cache.has("msg-1"))


if __name__ == "__main__":
    unittest.main()
