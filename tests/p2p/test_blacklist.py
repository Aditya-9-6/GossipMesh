import unittest
import time
from gossipmesh.p2p.blacklist import AdaptivePeerBlacklist, BlacklistConfig


class TestAdaptivePeerBlacklist(unittest.TestCase):
    def setUp(self):
        self.config = BlacklistConfig(
            window_seconds=10.0,
            max_failures=3,
            quarantine_seconds=20.0
        )
        self.blacklist = AdaptivePeerBlacklist(self.config)

    def test_normal_operation_below_threshold(self):
        peer_id = "peer-node-1"
        now = 100.0
        
        # Record 2 failures (below max_failures=3)
        self.assertFalse(self.blacklist.record_failure(peer_id, now=now))
        self.assertFalse(self.blacklist.record_failure(peer_id, now=now + 1.0))
        
        self.assertFalse(self.blacklist.is_blacklisted(peer_id, now=now + 2.0))
        metrics = self.blacklist.get_metrics(now=now + 2.0)
        self.assertEqual(metrics["tracked_peers"], 1)
        self.assertEqual(metrics["active_quarantines"], 0)

    def test_threshold_triggers_quarantine(self):
        peer_id = "peer-node-2"
        now = 100.0
        
        self.assertFalse(self.blacklist.record_failure(peer_id, now=now))
        self.assertFalse(self.blacklist.record_failure(peer_id, now=now + 2.0))
        # 3rd failure hits threshold
        self.assertTrue(self.blacklist.record_failure(peer_id, now=now + 4.0))
        
        self.assertTrue(self.blacklist.is_blacklisted(peer_id, now=now + 5.0))
        self.assertTrue(self.blacklist.is_blacklisted(peer_id, now=now + 19.0))
        
        metrics = self.blacklist.get_metrics(now=now + 5.0)
        self.assertEqual(metrics["active_quarantines"], 1)

    def test_quarantine_expiration(self):
        peer_id = "peer-node-3"
        now = 100.0
        
        for i in range(3):
            self.blacklist.record_failure(peer_id, now=now + i)
            
        self.assertTrue(self.blacklist.is_blacklisted(peer_id, now=now + 5.0))
        
        # Quarantine lasts 20s (until now + 4 + 20 = 124.0 approx, or 100 + 20 + buffer)
        # Quarantine ends at now (100) + 2 + 20 = 122.0 (since last failure was at now + 2)
        self.assertFalse(self.blacklist.is_blacklisted(peer_id, now=now + 25.0))

    def test_sliding_window_expiration(self):
        peer_id = "peer-node-4"
        now = 100.0
        
        # Record 2 failures at t=100 and t=101
        self.blacklist.record_failure(peer_id, now=now)
        self.blacklist.record_failure(peer_id, now=now + 1.0)
        
        # Advance past window (window=10s), record new failure at t=112
        self.assertFalse(self.blacklist.record_failure(peer_id, now=now + 12.0))
        
        # Should not be blacklisted because older failures fell outside window
        self.assertFalse(self.blacklist.is_blacklisted(peer_id, now=now + 12.5))

    def test_clear_peer(self):
        peer_id = "peer-node-5"
        now = 100.0
        
        for _ in range(3):
            self.blacklist.record_failure(peer_id, now=now)
            
        self.assertTrue(self.blacklist.is_blacklisted(peer_id, now=now))
        self.blacklist.clear_peer(peer_id)
        self.assertFalse(self.blacklist.is_blacklisted(peer_id, now=now))


if __name__ == "__main__":
    unittest.main()
