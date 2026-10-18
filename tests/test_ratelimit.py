import unittest
import time
import asyncio
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig
from gossipmesh.p2p.transport import GossipTransport

class TestPeerRateLimiter(unittest.TestCase):
    def setUp(self):
        self.config = RateLimitConfig(capacity=5.0, refill_rate=10.0, burst_limit=10.0)
        self.limiter = PeerRateLimiter(self.config)

    def test_normal_operation(self):
        peer_id = "peer_alpha"
        # Should allow up to capacity (5 tokens)
        for _ in range(5):
            self.assertTrue(self.limiter.acquire(peer_id))
        # Next should fail until refilled
        self.assertFalse(self.limiter.acquire(peer_id))

    def test_token_replenishment(self):
        peer_id = "peer_beta"
        for _ in range(5):
            self.assertTrue(self.limiter.acquire(peer_id))
        self.assertFalse(self.limiter.acquire(peer_id))
        
        # Wait for replenishment (refill_rate = 10 tokens/sec -> 0.2s yields 2 tokens)
        time.sleep(0.25)
        self.assertTrue(self.limiter.acquire(peer_id))
        self.assertTrue(self.limiter.acquire(peer_id))
        self.assertFalse(self.limiter.acquire(peer_id))

    def test_metrics(self):
        peer_id = "peer_gamma"
        self.limiter.acquire(peer_id)
        self.limiter.acquire(peer_id)
        metrics = self.limiter.get_metrics()
        self.assertEqual(metrics["allowed_count"], 2)
        self.assertEqual(metrics["active_peers"], 1)

class TestGossipTransportRateLimiting(unittest.TestCase):
    def setUp(self):
        self.transport = GossipTransport("node_1", RateLimitConfig(capacity=2.0, refill_rate=1.0))

    def test_transport_send_rate_limit(self):
        async def run():
            res1 = await self.transport.send_payload("peer_delta", {"msg": 1})
            res2 = await self.transport.send_payload("peer_delta", {"msg": 2})
            res3 = await self.transport.send_payload("peer_delta", {"msg": 3})
            self.assertTrue(res1)
            self.assertTrue(res2)
            self.assertFalse(res3)
            metrics = await self.transport.get_telemetry_metrics()
            self.assertEqual(metrics["dropped_count"], 1)
        asyncio.run(run())

if __name__ == "__main__":
    unittest.main()
