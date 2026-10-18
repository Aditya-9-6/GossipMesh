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
        self.rep.add_penalty("peer_1", 40.0)
        time.sleep(0.2)
        score = self.rep.get_score("peer_1")
        self.assertLess(score, 40.0)

    def test_reset_peer(self):
        self.rep.add_penalty("peer_1", 60.0)
        self.assertTrue(self.rep.is_quarantined("peer_1"))
        self.rep.reset_peer("peer_1")
        self.assertFalse(self.rep.is_quarantined("peer_1"))
        self.assertEqual(self.rep.get_score("peer_1"), 0.0)

if __name__ == '__main__':
    unittest.main()
