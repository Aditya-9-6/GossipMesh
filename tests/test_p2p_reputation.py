import unittest
import time
import asyncio
from gossipmesh.p2p.reputation import LeakyBucketReputation
from gossipmesh.p2p.transport import GossipTransport

class TestLeakyBucketReputation(unittest.TestCase):
    def setUp(self):
        self.rep = LeakyBucketReputation(capacity=100.0, leak_rate_per_sec=10.0, quarantine_threshold=50.0)

    def test_initial_state(self):
        self.assertFalse(self.rep.is_quarantined("peer_1"))
        self.assertEqual(self.rep.get_score("peer_1"), 0.0)

    def test_penalty_and_quarantine(self):
        # Add penalty below threshold
        quarantined = self.rep.add_penalty("peer_1", 30.0)
        self.assertFalse(quarantined)
        self.assertFalse(self.rep.is_quarantined("peer_1"))
        self.assertEqual(self.rep.get_score("peer_1"), 30.0)

        # Add penalty exceeding threshold
        quarantined = self.rep.add_penalty("peer_1", 30.0)
        self.assertTrue(quarantined)
        self.assertTrue(self.rep.is_quarantined("peer_1"))

    def test_leaking_over_time(self):
        self.rep.add_penalty("peer_2", 60.0)
        self.assertTrue(self.rep.is_quarantined("peer_2"))
        
        # Wait for leak (leak rate 10/s, need 10 to drop below 50)
        time.sleep(1.1)
        self.assertFalse(self.rep.is_quarantined("peer_2"))

    def test_reset_peer(self):
        self.rep.add_penalty("peer_3", 80.0)
        self.assertTrue(self.rep.is_quarantined("peer_3"))
        self.rep.reset_peer("peer_3")
        self.assertFalse(self.rep.is_quarantined("peer_3"))
        self.assertEqual(self.rep.get_score("peer_3"), 0.0)

class TestGossipTransportReputationIntegration(unittest.TestCase):
    def setUp(self):
        self.transport = GossipTransport(node_id="node_test")

    def test_transport_quarantine_drop(self):
        peer = "malicious_peer"
        self.transport.reputation.add_penalty(peer, 100.0)
        
        async def run():
            res = await self.transport.send_payload(peer, "hello")
            self.assertFalse(res)
            rec = await self.transport.receive_payload(peer, "hello")
            self.assertIsNone(rec)
            metrics = await self.transport.get_telemetry_metrics()
            self.assertEqual(metrics["transport"]["dropped_count"], 2)

        asyncio.run(run())

if __name__ == '__main__':
    unittest.main()
