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
        allowed1, _ = self.throttler.update_and_check(800)
        self.assertTrue(allowed1)
        # Exceed capacity
        allowed2, _ = self.throttler.update_and_check(500)
        self.assertFalse(allowed2)

    def test_gossip_transport_integration(self):
        transport = GossipTransport(node_id="node-throttler-test")
        self.assertIsNotNone(transport.bandwidth_throttler)
