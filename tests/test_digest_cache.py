import unittest
import time
import threading
from gossipmesh.p2p.digest import LRUDigestCache


class TestLRUDigestCache(unittest.TestCase):
    def test_basic_add_and_contains(self):
        cache = LRUDigestCache(max_size=3, default_ttl=60.0)
        self.assertFalse(cache.contains("msg1"))
        cache.add("msg1")
        self.assertTrue(cache.contains("msg1"))
        self.assertEqual(len(cache), 1)

    def test_lru_eviction(self):
        cache = LRUDigestCache(max_size=2, default_ttl=60.0)
        cache.add("msg1")
        cache.add("msg2")
        # Access msg1 so that msg2 becomes the least recently used
        self.assertTrue(cache.contains("msg1"))

        # Adding msg3 should evict the least recently used, which is msg2
        cache.add("msg3")
        self.assertTrue(cache.contains("msg1"))
        self.assertFalse(cache.contains("msg2"))
        self.assertTrue(cache.contains("msg3"))
        self.assertEqual(len(cache), 2)

    def test_ttl_expiry(self):
        cache = LRUDigestCache(max_size=10, default_ttl=0.1)
        cache.add("msg_expire")
        self.assertTrue(cache.contains("msg_expire"))
        time.sleep(0.2)
        self.assertFalse(cache.contains("msg_expire"))
        self.assertEqual(len(cache), 0)

    def test_concurrent_access(self):
        cache = LRUDigestCache(max_size=1000, default_ttl=60.0)

        def worker(start_idx: int):
            for i in range(100):
                msg_id = f"msg_{start_idx}_{i}"
                cache.add(msg_id)
                cache.contains(msg_id)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertLessEqual(len(cache), 1000)


if __name__ == "__main__":
    unittest.main()
