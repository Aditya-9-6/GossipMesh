import unittest
import time
from gossipmesh.p2p.ratelimit import TokenBucketRateLimiter
from gossipmesh.p2p.transport import P2PTransport

class TestTokenBucketRateLimiter(unittest.TestCase):
    def test_allow_within_capacity(self):
        limiter = TokenBucketRateLimiter(capacity=10.0, refill_rate=1.0)
        self.assertTrue(limiter.allow("peer1", cost=5.0))
        self.assertTrue(limiter.allow("peer1", cost=5.0))
        self.assertFalse(limiter.allow("peer1", cost=1.0))

    def test_refill_tokens(self):
        limiter = TokenBucketRateLimiter(capacity=10.0, refill_rate=10.0)
        self.assertTrue(limiter.allow("peer2", cost=10.0))
        self.assertFalse(limiter.allow("peer2", cost=1.0))
        # Wait for refill
        time.sleep(0.2)
        self.assertTrue(limiter.allow("peer2", cost=1.0))

    def test_transport_integration(self):
        transport = P2PTransport(capacity=5.0, refill_rate=1.0)
        self.assertTrue(transport.handle_message("peer3", payload_size=3.0))
        self.assertFalse(transport.handle_message("peer3", payload_size=3.0))
        self.assertEqual(transport.dropped_messages, 1)
        self.assertEqual(transport.accepted_messages, 1)

if __name__ == "__main__":
    unittest.main()
