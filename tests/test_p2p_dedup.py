import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from gossipmesh.p2p.dedup import DedupCache

class TestDedupCache(unittest.TestCase):
    def test_normal_operation(self):
        cache = DedupCache(capacity=10, default_ttl=5.0)
        
        # First time should be new (True)
        self.assertTrue(cache.check_and_add("msg-1"))
        # Immediate duplicate should return False
        self.assertFalse(cache.check_and_add("msg-1"))
        
        # Different message should be new
        self.assertTrue(cache.check_and_add("msg-2"))
        
        # Contains checks
        self.assertTrue(cache.contains("msg-1"))
        self.assertTrue(cache.contains("msg-2"))
        self.assertFalse(cache.contains("msg-3"))

    def test_ttl_expiration(self):
        # Very short TTL
        cache = DedupCache(capacity=10, default_ttl=0.1)
        self.assertTrue(cache.check_and_add("msg-expire"))
        self.assertFalse(cache.check_and_add("msg-expire"))
        
        # Wait for TTL to elapse
        time.sleep(0.2)
        
        # Should be treated as new again after expiration
        self.assertTrue(cache.check_and_add("msg-expire"))

    def test_capacity_eviction(self):
        cache = DedupCache(capacity=3, default_ttl=10.0)
        self.assertTrue(cache.check_and_add("a"))
        self.assertTrue(cache.check_and_add("b"))
        self.assertTrue(cache.check_and_add("c"))
        
        # Cache is now full (capacity 3). Adding "d" should evict "a".
        self.assertTrue(cache.check_and_add("d"))
        
        self.assertFalse(cache.contains("a"))
        self.assertTrue(cache.contains("b"))
        self.assertTrue(cache.contains("c"))
        self.assertTrue(cache.contains("d"))
        
        # "a" was evicted, so adding "a" again should succeed
        self.assertTrue(cache.check_and_add("a"))

    def test_edge_cases(self):
        cache = DedupCache(capacity=5)
        self.assertFalse(cache.check_and_add(""))
        self.assertFalse(cache.contains(""))
        
        cache.clear()
        self.assertFalse(cache.contains("msg-1"))

    def test_concurrency_safety(self):
        cache = DedupCache(capacity=1000, default_ttl=10.0)
        num_threads = 20
        iterations_per_thread = 100

        def worker(thread_idx):
            for i in range(iterations_per_thread):
                msg_id = f"msg-{thread_idx}-{i}"
                cache.check_and_add(msg_id)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, t) for t in range(num_threads)]
            for f in futures:
                f.result()

        # Verify that all unique messages were successfully recorded
        for t in range(num_threads):
            for i in range(iterations_per_thread):
                self.assertTrue(cache.contains(f"msg-{t}-{i}"))

if __name__ == "__main":
    unittest.main()
