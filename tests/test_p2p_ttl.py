import unittest
from gossipmesh.p2p.ttl import AdaptiveTTLEngine

class TestAdaptiveTTLEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AdaptiveTTLEngine(base_ttl=10, max_queue_depth=100, max_latency_ms=500.0)

    def test_high_congestion_decay(self):
        # High queue depth and latency should result in aggressive decay
        new_ttl = self.engine.calculate_decay(current_ttl=10, queue_depth=90, latency_ms=450.0)
        self.assertLess(new_ttl, 7)

    def test_low_congestion_decay(self):
        new_ttl = self.engine.calculate_decay(current_ttl=10, queue_depth=5, latency_ms=10.0)
        self.assertGreaterEqual(new_ttl, 8)

    def test_poison_reverse(self):
        new_ttl = self.engine.calculate_decay(current_ttl=10, queue_depth=50, latency_ms=200.0, is_poison_reverse=True)
        self.assertEqual(new_ttl, 0)

if __name__ == "__main__":
    unittest.main()
