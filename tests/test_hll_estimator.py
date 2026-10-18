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

    def test_window_sliding_decay(self):
        now = time.time()
        hll = WindowedHyperLogLog(num_registers=1024, window_seconds=10)
        
        hll.add("old_peer", timestamp=now - 20)
        self.assertEqual(hll.count(current_time=now), 0)

        hll.add("recent_peer", timestamp=now - 2)
        self.assertEqual(hll.count(current_time=now), 1)

    def test_merge_operation(self):
        now = time.time()
        hll1 = WindowedHyperLogLog(num_registers=1024, window_seconds=60)
        hll2 = WindowedHyperLogLog(num_registers=1024, window_seconds=60)

        hll1.add("peer_a", timestamp=now)
        hll2.add("peer_b", timestamp=now)

        hll1.merge(hll2, current_time=now)
        est = hll1.count(current_time=now)
        self.assertGreaterEqual(est, 1)

if __name__ == "__main__":
    unittest.main()
