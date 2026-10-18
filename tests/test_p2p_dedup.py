import time
import unittest
import threading
from gossipmesh.p2p.dedup import RingBufferDedup

class TestRingBufferDedup(unittest.TestCase):
    def test_normal_operation(self):
        dedup = RingBufferDedup(capacity=3, default_ttl=5.0)
        self.assertTrue(dedup.check_and_add("msg-1"))
        self.assertFalse(dedup.check_and_add("msg-1"))
        self.assertTrue(dedup.contains("msg-1"))
        self.assertTrue(dedup.check_and_add("msg-2"))
        self.assertEqual(dedup.size(), 2)

    def test_capacity_eviction(self):
        dedup = RingBufferDedup(capacity=2, default_ttl=5.0)
        self.assertTrue(dedup.check_and_add("msg-1"))
        self.assertTrue(dedup.check_and_add("msg-2"))
        self.assertEqual(dedup.size(), 2)
        
        # Adding third should evict msg-1
        self.assertTrue(dedup.check_and_add("msg-3"))
        self.assertFalse(dedup.contains("msg-1"))
        self.assertTrue(dedup.contains("msg-2"))
        self.assertTrue(dedup.contains("msg-3"))
        self.assertEqual(dedup.size(), 2)

    def test_ttl_expiration(self):
        dedup = RingBufferDedup(capacity=10, default_ttl=0.1)
        self.assertTrue(dedup.check_and_add("msg-ttl"))
        self.assertTrue(dedup.contains("msg-ttl"))
        time.sleep(0.15)
        self.assertFalse(dedup.contains("msg-ttl"))
        # Should allow re-adding after TTL expiration
        self.assertTrue(dedup.check_and_add("msg-ttl"))

    def test_concurrent_access(self):
        dedup = RingBufferDedup(capacity=1000, default_ttl=10.0)
        def worker(start_idx: int):
            for i in range(100):
                dedup.check_and_add(f"msg-{start_idx}-{i}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertGreaterEqual(dedup.size(), 1)

if __name__ == "__main__":
    unittest.main()
