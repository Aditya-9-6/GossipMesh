import time
import threading
import unittest
from gossipmesh.p2p.dedup import RingBufferDedup


class TestRingBufferDedup(unittest.TestCase):
    def test_dedup_basic(self):
        dedup = RingBufferDedup(capacity=10, ttl=60.0)
        msg_id = b"msg_123"
        
        self.assertFalse(dedup.seen(msg_id))
        self.assertTrue(dedup.seen(msg_id))

    def test_capacity_eviction(self):
        dedup = RingBufferDedup(capacity=3, ttl=60.0)
        self.assertFalse(dedup.seen(b"1"))
        self.assertFalse(dedup.seen(b"2"))
        self.assertFalse(dedup.seen(b"3"))
        self.assertTrue(dedup.seen(b"1"))
        
        self.assertFalse(dedup.seen(b"4"))
        self.assertFalse(dedup.seen(b"2"))

    def test_ttl_expiration(self):
        dedup = RingBufferDedup(capacity=10, ttl=0.1)
        self.assertFalse(dedup.seen(b"expire_me"))
        self.assertTrue(dedup.seen(b"expire_me"))
        
        time.sleep(0.2)
        self.assertFalse(dedup.seen(b"expire_me"))

    def test_concurrent_access(self):
        dedup = RingBufferDedup(capacity=1000, ttl=60.0)
        
        def worker(start: int):
            for i in range(100):
                dedup.seen(f"msg_{start}_{i}".encode())
                
        threads = [threading.Thread(target=worker, args=(j,)) for j in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        self.assertGreater(len(dedup), 0)
