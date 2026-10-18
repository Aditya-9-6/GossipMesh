import unittest
import asyncio
import time
from gossipmesh.p2p.rate_limiter import PeerTrafficMeter, TokenBucketRateLimiter
from gossipmesh.p2p.connection_manager import P2PConnectionManager

class TestTokenBucketRateLimiter(unittest.TestCase):

    def test_peer_traffic_meter_basic(self):
        meter = PeerTrafficMeter(capacity=5.0, refill_rate=1.0)
        self.assertTrue(meter.consume(3.0))
        self.assertTrue(meter.consume(2.0))
        self.assertFalse(meter.consume(1.0))

    def test_rate_limiter_concurrency(self):
        async def run():
            limiter = TokenBucketRateLimiter(capacity=10.0, refill_rate=5.0, max_tracked_peers=2)
            res1 = await limiter.acquire("peerA", 5.0)
            res2 = await limiter.acquire("peerA", 6.0)
            self.assertTrue(res1)
            self.assertFalse(res2)

            # Test eviction bound
            await limiter.acquire("peerB", 1.0)
            await limiter.acquire("peerC", 1.0)
            self.assertNotIn("peerA", limiter._meters)

        asyncio.run(run())

    def test_connection_manager_shedding(self):
        async def run():
            mgr = P2PConnectionManager(max_connections=2)
            admit1 = await mgr.admit_connection("p1", priority=1)
            self.assertTrue(admit1)
            await mgr.register_connection("p1", None, priority=1)

            admit2 = await mgr.admit_connection("p2", priority=2)
            self.assertTrue(admit2)
            await mgr.register_connection("p2", None, priority=2)

            # p3 has higher priority than p1 (1), should evict p1
            admit3 = await mgr.admit_connection("p3", priority=5)
            self.assertTrue(admit3)
            self.assertNotIn("p1", mgr.active_connections)

        asyncio.run(run())

if __name__ == "__main__":
    unittest.main()
