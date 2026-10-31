import time
import unittest
from gossipmesh.p2p.transport import WindowedEMABandwidthThrottler


class TestWindowedEMABandwidthThrottler(unittest.TestCase):
    def test_initial_state(self):
        throttler = WindowedEMABandwidthThrottler(max_bytes_per_sec=1000.0, alpha=0.5)
        self.assertEqual(throttler.get_current_rate(), 0.0)

    def test_normal_operation_within_limits(self):
        throttler = WindowedEMABandwidthThrottler(max_bytes_per_sec=10000.0, alpha=0.3)
        # Small transfer should be allowed
        allowed = throttler.update_and_check(500)
        self.assertTrue(allowed)
        self.assertGreater(throttler.get_current_rate(), 0.0)

    def test_burst_throttling_boundary(self):
        # Capacity = 1000 * 1.5 = 1500 bytes
        throttler = WindowedEMABandwidthThrottler(max_bytes_per_sec=1000.0, alpha=0.2, burst_multiplier=1.5)

        # Exhaust tokens beyond capacity
        allowed = throttler.update_and_check(2000)
        self.assertFalse(allowed)

        # Reasonable transfer should pass
        allowed_normal = throttler.update_and_check(100)
        self.assertTrue(allowed_normal)

    def test_ema_smoothing(self):
        throttler = WindowedEMABandwidthThrottler(max_bytes_per_sec=50000.0, alpha=0.5)
        time.sleep(0.01)
        throttler.update_and_check(1000)
        rate1 = throttler.get_current_rate()

        time.sleep(0.01)
        throttler.update_and_check(5000)
        rate2 = throttler.get_current_rate()

        self.assertNotEqual(rate1, rate2)


if __name__ == "__main__":
    unittest.main()
