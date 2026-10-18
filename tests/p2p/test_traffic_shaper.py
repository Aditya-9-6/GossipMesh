import unittest
import time
from gossipmesh.p2p.traffic_shaper import LeakyBucketTrafficShaper, TokenBucketConfig, PeerTrafficShaperManager

class TestTrafficShaper(unittest.TestCase):
    def test_token_bucket_normal(self):
        config = TokenBucketConfig(capacity=100.0, refill_rate=10.0)
        shaper = LeakyBucketTrafficShaper(config)
        
        # Should allow consume within capacity
        self.assertTrue(shaper.consume(50))
        metrics = shaper.get_metrics()
        self.assertEqual(metrics["total_shaped_bytes"], 50)
        self.assertEqual(metrics["total_dropped_bytes"], 0)
        
        # Should reject consume exceeding tokens
        self.assertFalse(shaper.consume(60))
        metrics = shaper.get_metrics()
        self.assertEqual(metrics["total_dropped_bytes"], 60)

    def test_token_bucket_refill(self):
        config = TokenBucketConfig(capacity=100.0, refill_rate=1000.0)
        shaper = LeakyBucketTrafficShaper(config)
        
        # Exhaust tokens
        self.assertTrue(shaper.consume(100))
        self.assertFalse(shaper.consume(10))
        
        # Simulate time passage
        time.sleep(0.05)
        
        # Should now permit consume
        self.assertTrue(shaper.consume(10))

    def test_peer_shaper_manager(self):
        manager = PeerTrafficShaperManager(TokenBucketConfig(capacity=200.0, refill_rate=50.0))
        shaper1 = manager.get_shaper("peer_a")
        shaper2 = manager.get_shaper("peer_b")
        
        self.assertIsNotNone(shaper1)
        self.assertIsNotNone(shaper2)
        self.assertEqual(shaper1, manager.get_shaper("peer_a"))

        manager.remove_peer("peer_a")

if __name__ == "__main__":
    unittest.main()
