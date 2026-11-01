import time
import threading
import unittest
from gossipmesh.p2p.digest import LruDigestCache


class TestLruDigestCache(unittest.TestCase):
    def test_basic_add_and_contains(self):
        cache = LruDigestCache(max_size=3, default_ttl=60.0)
        self.assertFalse("msg1" in cache)
        cache.add("msg1")
        self.assertTrue("msg1" in cache)
        self.assertEqual(cache.get_size(), 1)

    def test_lru_eviction(self):
        cache = LruDigestCache(max_size=2, default_ttl=60.0)
        cache.add("msg1")
        cache.add("msg2")
        self.assertTrue("msg1" in cache)
        self.assertTrue("msg2" in cache)

        # Access msg1 so msg2 becomes the oldest
        self.assertTrue("msg1" in cache)

        # Adding msg3 should evict msg2
        cache.add("msg3")
        self.assertTrue("msg1" in cache)
        self.assertFalse("msg2" in cache)
        self.assertTrue("msg3" in cache)
        self.assertEqual(cache.get_size(), 2)

    def test_ttl_expiration(self):
        cache = LruDigestCache(max_size=10, default_ttl=0.1)
        cache.add("msg_ttl")
        self.assertTrue("msg_ttl" in cache)
        time.sleep(0.15)
        self.assertFalse("msg_ttl" in cache)
        self.assertEqual(cache.get_size(), 0)

    def test_custom_ttl(self):
        cache = LruDigestCache(max_size=10, default_ttl=0.05)
        cache.add("short_ttl", ttl=0.01)
        cache.add("long_ttl", ttl=2.0)
        time.sleep(0.08)
        self.assertFalse("short_ttl" in cache)
        self.assertTrue("long_ttl" in cache)

    def test_concurrent_access(self):
        cache = LruDigestCache(max_size=1000, default_ttl=10.0)

        def worker(start_idx: int):
            for i in range(100):
                msg_id = f"msg_{start_idx}_{i}"
                cache.add(msg_id)
                _ = msg_id in cache

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertGreater(cache.get_size(), 0)
        cache.clear()
        self.assertEqual(cache.get_size(), 0)


if __name__ == "__main અમારા":
    unittest.main()
