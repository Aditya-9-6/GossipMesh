import unittest
import threading
from gossipmesh.p2p.dedup import CompressedBloomFilter
from gossipmesh.p2p.transport import GossipTransport

class TestCompressedBloomFilter(unittest.TestCase):
    def test_bloom_filter_basic(self):
        bf = CompressedBloomFilter(capacity=1000, error_rate=0.01)
        self.assertLessEqual(bf.memory_usage_bytes(), 65536)
        
        msg_id = "msg_abc123"
        self.assertNotIn(msg_id, bf)
        bf.add(msg_id)
        self.assertIn(msg_id, bf)

    def test_sliding_window_reset(self):
        bf = CompressedBloomFilter(capacity=5, error_rate=0.01)
        for i in range(6):
            bf.add(f"msg_{i}")
        # Capacity exceeded, buffer should clear
        self.assertNotIn("msg_0", bf)

    def test_transport_deduplication(self):
        transport = GossipTransport(capacity=100, error_rate=0.01)
        msg_id = "unique_gossip_id"
        
        self.assertTrue(transport.should_process_message(msg_id))
        self.assertFalse(transport.should_process_message(msg_id))

    def test_concurrency_safety(self):
        bf = CompressedBloomFilter(capacity=5000, error_rate=0.01)
        def worker(start: int):
            for i in range(start, start + 100):
                bf.add(f"concurrent_{i}")
                
        threads = [threading.Thread(target=worker, args=(i * 100,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        self.assertIn("concurrent_450", bf)

if __name__ == "__main__":
    unittest.main()
