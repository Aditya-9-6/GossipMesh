import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from gossipmesh.p2p.dedup import DedupCache


class TestDedupCache(unittest.TestCase):
    def test_normal_operation(self):
        cache = DedupCache(capacity=10, default_ttl=5.0)

        self.assertTrue(cache.check_and_add("msg-1"))
        self.assertFalse(cache.check_and_add("msg-1"))
        self.assertTrue(cache.check_and_add("msg-2"))
        self.assertTrue(cache.contains("msg-1"))
        self.assertTrue(cache.contains("msg-2"))

    def test_ttl_expiration(self):
        cache = DedupCache(capacity=10, default_ttl=0.1)
        self.assertTrue(cache.check_and_add("msg-expire"))
        self.assertFalse(cache.check_and_add("msg-expire"))
        time.sleep(0.2)
        self.assertTrue(cache.check_and_add("msg-expire"))

    def test_capacity_eviction(self):
        cache = DedupCache(capacity=2, default_ttl=10.0)
        self.assertTrue(cache.check_and_add("msg-A"))
        self.assertTrue(cache.check_and_add("msg-B"))
        self.assertTrue(cache.check_and_add("msg-C"))
        self.assertFalse(cache.contains("msg-A"))
        self.assertTrue(cache.contains("msg-B"))
        self.assertTrue(cache.contains("msg-C"))

    def test_concurrency_safety(self):
        cache = DedupCache(capacity=50000, default_ttl=10.0)
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

        for t in range(num_threads):
            for i in range(iterations_per_thread):
                self.assertTrue(cache.contains(f"msg-{t}-{i}"))


if __name__ == "__main__":
    unittest.main()
