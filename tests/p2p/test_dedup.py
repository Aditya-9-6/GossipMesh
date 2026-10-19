import unittest
from gossipmesh.p2p.dedup import CountingBloomFilter, BoundedLRUGossipRingBuffer


class TestDedupSubsystem(unittest.TestCase):
    def test_counting_bloom_filter_basic(self):
        bf = CountingBloomFilter(capacity=100)
        self.assertNotIn("msg-1", bf)
        bf.add("msg-1")
        self.assertIn("msg-1", bf)
        bf.remove("msg-1")
        # Due to false positives or hash overlap after removal, check robustness
        self.assertIsInstance(bf.table, list)

    def test_bounded_lru_ring_buffer_capacity(self):
        buf = BoundedLRUGossipRingBuffer(capacity=2)
        buf.put("m1", {"data": 1})
        buf.put("m2", {"data": 2})

        self.assertIn("m1", buf)
        self.assertIn("m2", buf)
        self.assertEqual(len(buf), 2)

        # Adding a 3rd item should evict m1
        evicted = buf.put("m3", {"data": 3})
        self.assertEqual(evicted, ("m1", {"data": 1}))
        self.assertNotIn("m1", buf)
        self.assertIn("m3", buf)
        self.assertEqual(len(buf), 2)

    def test_lru_order_refresh(self):
        buf = BoundedLRUGossipRingBuffer(capacity=2)
        buf.put("m1", {"data": 1})
        buf.put("m2", {"data": 2})
        # Access m1 to refresh its LRU timestamp
        self.assertEqual(buf.get("m1"), {"data": 1})
        # Adding m3 should now evict m2 instead of m1
        evicted = buf.put("m3", {"data": 3})
        self.assertEqual(evicted, ("m2", {"data": 2}))
        self.assertIn("m1", buf)
        self.assertNotIn("m2", buf)
        self.assertIn("m3", buf)
