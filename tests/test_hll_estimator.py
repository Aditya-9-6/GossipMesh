import unittest
import time
from gossipmesh.p2p.hll import WindowedHyperLogLog


class TestWindowedHyperLogLog(unittest.TestCase):
    def test_basic_cardinality(self):
        hll = WindowedHyperLogLog(num_registers=1024, window_seconds=60.0)
        peers = [f"peer-{i}" for i in range(500)]
        for p in peers:
            hll.add(p)
        
        est = hll.estimate()
        self.assertTrue(300 <= est <= 800, f"Estimate {est} out of bounds for 500 unique elements")

    def test_window_expiration(self):
        now = 1000.0
        hll = WindowedHyperLogLog(num_registers=256, window_seconds=10.0)
        hll.add("peer-a", current_time=now)
        self.assertGreater(hll.estimate(current_time=now), 0)
        
        # After window expiration
        expired_time = now + 15.0
        self.assertEqual(hll.estimate(current_time=expired_time), 0)

    def test_merge_estimators(self):
        now = time.time()
        hll1 = WindowedHyperLogLog(num_registers=256, window_seconds=60.0)
        hll2 = WindowedHyperLogLog(num_registers=256, window_seconds=60.0)

        hll1.add("peer-1", current_time=now)
        hll2.add("peer-2", current_time=now)

        hll1.merge(hll2, current_time=now)
        est = hll1.estimate(current_time=now)
        self.assertGreaterEqual(est, 1)

    def test_zero_estimate(self):
        hll = WindowedHyperLogLog(num_registers=64)
        self.assertEqual(hll.estimate(), 0)


if __name__ == '__main__':
    unittest.main()
