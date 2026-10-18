import unittest
import time
import asyncio
from gossipmesh.p2p.transport import WindowedEMABandwidthThrottler, GossipTransport
from gossipmesh.p2p.ratelimit import RateLimitConfig

class TestWindowedEMABandwidthThrottler(unittest.TestCase):
    def setUp(self):
        # Capacity 1000 bytes, refill rate 5000 bytes/sec
        self.throttler = WindowedEMABandwidthThrottler(capacity=1000.0, refill_rate=5000.0, alpha=0.5)

    def test_normal_operation(self):
        allowed, rate = self.throttler.update_and_check(100)
        self.assertTrue(allowed)
        self.assertGreaterEqual(rate, 0.0)

    def test_burst_throttling(self):
        # Exceed capacity of 1000 bytes instantly
        allowed, rate = self.throttler.update_and_check(2000)
        self.assertFalse(allowed)

    def test_reset(self):
        self.throttler.update_and_check(500)
        self.throttler.reset()
        self.assertEqual(self.throttler.get_rate(), 0.0)

    def test_gossip_transport_integration(self):
        async def run_integration():
            transport = GossipTransport(node_id="node-1")
            res = await transport.send_payload("peer-2", {"msg": "hello"})
            self.assertTrue(res)
            metrics = await transport.get_telemetry_metrics()
            self.assertIn("ema_bandwidth_rate", metrics)
            self.assertEqual(metrics["sent_bytes"], 17)
        
        asyncio.run(run_integration())

if __name__ == '__main__':
    unittest.main()
