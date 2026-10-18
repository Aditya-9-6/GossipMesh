import time
import unittest
from gossipmesh.crypto.epoch import get_current_epoch, get_epoch_time_window, is_epoch_valid, EPOCH_DURATION_SECONDS

class TestCryptoEpoch(unittest.TestCase):
    def test_get_current_epoch(self):
        now = 120.0
        self.assertEqual(get_current_epoch(now), 2)

    def test_get_epoch_time_window(self):
        start, end = get_epoch_time_window(2)
        self.assertEqual(start, 120.0)
        self.assertEqual(end, 180.0)

    def test_is_epoch_valid(self):
        current = get_current_epoch(1000.0)
        self.assertTrue(is_epoch_valid(current, tolerance_epochs=1, timestamp=1000.0))
        self.assertTrue(is_epoch_valid(current - 1, tolerance_epochs=1, timestamp=1000.0))
        self.assertFalse(is_epoch_valid(current - 2, tolerance_epochs=1, timestamp=1000.0))
        self.assertFalse(is_epoch_valid(current + 2, tolerance_epochs=1, timestamp=1000.0))

if __name__ == "__main__":
    unittest.main()
