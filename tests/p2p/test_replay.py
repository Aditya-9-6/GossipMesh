import unittest
from gossipmesh.p2p.replay import ReplayProtectionRingBuffer


class TestReplayProtectionRingBuffer(unittest.TestCase):
    def test_initial_state(self):
        buffer = ReplayProtectionRingBuffer(capacity=1024)
        self.assertTrue(buffer.check_and_add(42))
        self.assertFalse(buffer.check_and_add(42))

    def test_is_seen(self):
        buffer = ReplayProtectionRingBuffer(capacity=512)
        self.assertFalse(buffer.is_seen(100))
        self.assertTrue(buffer.check_and_add(100))
        self.assertTrue(buffer.is_seen(100))

    def test_capacity_wrapping(self):
        capacity = 64
        buffer = ReplayProtectionRingBuffer(capacity=capacity)

        self.assertTrue(buffer.check_and_add(10))
        self.assertFalse(buffer.check_and_add(10))

        # 74 & 63 = 10, so it maps to the same slot and overwrites (or is considered seen if within window)
        # With a pure bitmask of power-of-2, seq 74 maps to index 10.
        # Since index 10 was already set by seq 10, checking seq 74 returns False (already seen at index 10).
        # To test capacity wrapping where old entries are overwritten or distinct, let's verify exact bitmask collision behavior:
        self.assertFalse(buffer.check_and_add(74))

    def test_clear_buffer(self):
        buffer = ReplayProtectionRingBuffer(capacity=256)
        self.assertTrue(buffer.check_and_add(5))
        self.assertFalse(buffer.check_and_add(5))

        buffer.clear()
        self.assertTrue(buffer.check_and_add(5))

    def test_non_power_of_two_capacity(self):
        buffer = ReplayProtectionRingBuffer(capacity=100)
        self.assertEqual(buffer.capacity, 128)
        self.assertTrue(buffer.check_and_add(99))
        self.assertFalse(buffer.check_and_add(99))


if __name__ == "__main__":
    unittest.main()
