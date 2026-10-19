import unittest
import asyncio
import time
from gossipmesh.p2p.ratelimit import TokenBucket, RateLimitConfig, PeerRateLimiter


class TestTokenBucket(unittest.TestCase):
    def test_token_bucket_basic(self):
        bucket = TokenBucket(capacity=10.0, refill_rate=5.0, initial_tokens=10.0)
        self.assertTrue(bucket.consume(5.0))
        self.assertAlmostEqual(bucket.tokens, 5.0, places=1)
        self.assertFalse(bucket.consume(6.0))
        self.assertTrue(bucket.consume(5.0))
        self.assertAlmostEqual(bucket.tokens, 0.0, places=1)

    def test_token_bucket_refill(self):
        bucket = TokenBucket(capacity=10.0, refill_rate=100.0, initial_tokens=0.0)
        time.sleep(0.05)
        self.assertTrue(bucket.can_consume(1.0))
        self.assertTrue(bucket.consume(1.0))


class TestPeerRateLimiter(unittest.TestCase):
    def setUp(self):
        self.config = RateLimitConfig(max_tokens=5.0, refill_rate=10.0, max_bytes_per_sec=100.0, max_peers=2)
        self.limiter = PeerRateLimiter(self.config)

    def test_rate_limiting_flow(self):
        async def run():
            # Consume all tokens
            for _ in range(5):
                allowed, reason = await self.limiter.check_and_consume("peer_1", 10)
                self.assertTrue(allowed)
                self.assertEqual(reason, "allowed")

            # 6th should exceed rate limit
            allowed, reason = await self.limiter.check_and_consume("peer_1", 10)
            self.assertFalse(allowed)
            self.assertEqual(reason, "rate_limit_exceeded")

        asyncio.run(run())

    def test_bandwidth_limiting_flow(self):
        async def run():
            # Consume exceeding bandwidth (> 100 bytes)
            allowed, reason = await self.limiter.check_and_consume("peer_2", 150)
            self.assertFalse(allowed)
            self.assertEqual(reason, "bandwidth_limit_exceeded")

        asyncio.run(run())

    def test_lru_eviction(self):
        async def run():
            await self.limiter.check_and_consume("peer_a", 1)
            await self.limiter.check_and_consume("peer_b", 1)
            metrics = await self.limiter.get_metrics()
            self.assertEqual(metrics["active_peers"], 2)

            # Adding peer_c should evict peer_a
            await self.limiter.check_and_consume("peer_c", 1)
            metrics = await self.limiter.get_metrics()
            self.assertEqual(metrics["active_peers"], 2)

            # Reset peer_c
            await self.limiter.reset_peer("peer_c")
            metrics_after = await self.limiter.get_metrics()
            self.assertEqual(metrics_after["active_peers"], 1)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
