import unittest
from gossipmesh.p2p.cache import GossipMessageCache


class TestGossipMessageCache(unittest.TestCase):
    def test_init_validation(self):
        with self.assertRaises(ValueError):
            GossipMessageCache(capacity=0)
        with self.assertRaises(ValueError):
            GossipMessageCache(capacity=-5)

    def test_basic_put_and_get(self):
        cache = GossipMessageCache(capacity=3)
        cache.put("msg-1", {"data": "hello"})

        self.assertTrue(cache.has("msg-1"))
        self.assertIn("msg-1", cache)
        self.assertEqual(cache.get("msg-1"), {"data": "hello"})
        self.assertIsNone(cache.get("non-existent"))

    def test_lru_eviction(self):
        cache = GossipMessageCache(capacity=2)
        cache.put("msg-1", "val1")
        cache.put("msg-2", "val2")

        self.assertEqual(len(cache), 2)
        self.assertTrue(cache.has("msg-1"))
        self.assertTrue(cache.has("msg-2"))

        # Inserting a 3rd item should evict the oldest ("msg-1")
        cache.put("msg-3", "val3")
        self.assertEqual(len(cache), 2)
        self.assertFalse(cache.has("msg-1"))
        self.assertTrue(cache.has("msg-2"))
        self.assertTrue(cache.has("msg-3"))

    def test_lru_order_refresh_on_get(self):
        cache = GossipMessageCache(capacity=2)
        cache.put("msg-1", "val1")
        cache.put("msg-2", "val2")

        # Access "msg-1" so it becomes most recently used
        cache.get("msg-1")

        # Insert "msg-3", which should evict "msg-2" instead of "msg-1"
        cache.put("msg-3", "val3")

        self.assertTrue(cache.has("msg-1"))
        self.assertFalse(cache.has("msg-2"))
        self.assertTrue(cache.has("msg-3"))

    def test_clear_cache(self):
        cache = GossipMessageCache(capacity=10)
        cache.put("msg-1", "val1")
        cache.put("msg-2", "val2")
        self.assertEqual(len(cache), 2)

        cache.clear()
        self.assertEqual(len(cache), 0)
        self.assertFalse(cache.has("msg-1"))


if __name__ == "__main__":
    unittest.main()
