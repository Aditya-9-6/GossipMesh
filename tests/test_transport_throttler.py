import unittest
import time
import asyncio
from gossipmesh.p2p.transport import WindowedEMABandwidthThrottler, GossipTransport
from gossipmesh.p2p.ratelimit import RateLimitConfig


class TestWindowedEMABandwidthThrottler(unittest.TestCase):
    def setUp(self):
        self.throttler = WindowedEMABandwidthThrottler(capacity=1000.0, refill_rate=5000.0, alpha=0.3)

    def test_throttler_initial_state(self):
        self.assertEqual(self.throttler.get_rate(), 0.0)

    def test_update_and_check(self):
        now = time.time()
        allowed, rate = self.throttler.update_and_check(100, now=now)
        self.assertTrue(allowed)
        self.assertGreater(rate, 0.0)

    def test_reset(self):
        self.throttler.update_and_check(500)
        self.throttler.reset()
        self.assertEqual(self.throttler.get_rate(), 0.0)


class TestGossipTransportThrottler(unittest.IsolatedAsyncioTestCase):
    async def test_transport_send_receive_throttling(self):
        transport = GossipTransport(node_id="node-1")
        res = await transport.send_payload("peer-1", {"hello": "world"})
        self.assertTrue(res)
        metrics = await transport.get_telemetry_metrics()
        self.assertIn("ema_bandwidth_rate", metrics)
