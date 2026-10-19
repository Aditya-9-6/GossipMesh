import unittest
import time
from gossipmesh.p2p.hll import WindowedHyperLogLog

class TestWindowedHyperLogLog(unittest.TestCase):
    def test_initial_zero_cardinality(self):
        hll = WindowedHyperLogLog(num_registers=1024, window_seconds=60)
        self.assertEqual(hll.count(), 0)

    def test_cardinality_estimation(self):
        hll = WindowedHyperLogLog(num_registers=1024, window_seconds=60)
        items_added = 500
        for i in range(items_added):
            hll.add(f"peer_{i}")

        estimated = hll.count()
        error_margin = estimated * 0.25
        self.assertAlmostEqual(estimated, items_added, delta=error_margin + 150)

    def test_initialization_validation(self):
        with self.assertRaises(ValueError):
            WindowedHyperLogLog(num_registers=100) # Not power of 2
        with self.assertRaises(ValueError):
            WindowedHyperLogLog(num_registers=8) # Less than 16

    def test_basic_cardinality(self):
        hll = WindowedHyperLogLog(num_registers=1024, window_ttl=60.0)
        for i in range(500):
            hll.add(f"peer-{i}")
        
        est = hll.estimate()
        # HLL has probabilistic error bounds (~3% for m=1024), check within bounds
        self.assertTrue(350 <= est <= 650, f"Estimate {est} out of expected bounds for 500 unique elements")

    def test_duplicate_insertion(self):
        hll = WindowedHyperLogLog(num_registers=1024)
        for _ in range(10):
            for i in range(100):
                hll.add(f"peer-{i}")
        
        est = hll.estimate()
        self.assertTrue(80 <= est <= 120, f"Estimate {est} incorrect after duplicate insertions")

    def test_window_sliding_decay(self):
        now = time.time()
        hll = WindowedHyperLogLog(num_registers=1024, window_seconds=10)
        
        hll.add("old_peer", timestamp=now - 20)
        self.assertEqual(hll.count(current_time=now), 0)

        hll.add("recent_peer", timestamp=now - 2)
        self.assertEqual(hll.count(current_time=now), 1)

        hll2 = WindowedHyperLogLog(num_registers=256, window_ttl=10.0)
        t0 = 1000.0
        hll2.add("peer-a", current_time=t0)
        self.assertAlmostEqual(hll2.estimate(current_time=t0), 1.0, delta=1.0)
        
        # Advance time past TTL
        hll2.decay(current_time=t0 + 15.0)
        self.assertEqual(hll2.estimate(current_time=t0 + 15.0), 0.0)

    def test_merge_operation(self):
        now = time.time()
        hll1 = WindowedHyperLogLog(num_registers=1024, window_seconds=60)
        hll2 = WindowedHyperLogLog(num_registers=1024, window_seconds=60)

        hll1.add("peer_a", timestamp=now)
        hll2.add("peer_b", timestamp=now)

        hll1.merge(hll2, current_time=now)
        est = hll1.count(current_time=now)
        self.assertGreaterEqual(est, 1)

    def test_merge_estimators(self):
        hll1 = WindowedHyperLogLog(num_registers=512)
        hll2 = WindowedHyperLogLog(num_registers=512)
        
        for i in range(200):
            hll1.add(f"peer-a-{i}")
        for i in range(200):
            hll2.add(f"peer-b-{i}")
            
        hll1.merge(hll2)
        est = hll1.estimate()
        self.assertTrue(300 <= est <= 500, f"Merged estimate {est} out of bounds")

    def test_merge_validation(self):
        hll1 = WindowedHyperLogLog(num_registers=256)
        hll2 = WindowedHyperLogLog(num_registers=512)
        with self.assertRaises(ValueError):
            hll1.merge(hll2)
        with self.assertRaises(TypeError):
            hll1.merge("not-an-hll")

    def test_type_error_on_add(self):
        hll = WindowedHyperLogLog()
        with self.assertRaises(TypeError):
            hll.add(12345)

if __name__ == "__main__":
    unittest.main()
