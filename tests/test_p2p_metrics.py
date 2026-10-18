import time
import unittest
from gossipmesh.p2p.metrics import (
    BandwidthConfig,
    PeerTier,
    PeerTierManager,
    WindowedEWMABandwidthProfiler,
)


class TestWindowedEWMABandwidthProfiler(unittest.TestCase):
    def setUp(self):
        self.config = BandwidthConfig(
            alpha=0.5,
            window_seconds=10.0,
            high_tier_threshold_bps=1000.0,
            medium_tier_threshold_bps=100.0,
        )
        self.profiler = WindowedEWMABandwidthProfiler(self.config)

    def test_initial_state(self):
        self.assertEqual(self.profiler.get_bandwidth_bps(), 0.0)
        self.assertEqual(self.profiler.get_tier(), PeerTier.UNKNOWN)
        metrics = self.profiler.get_metrics()
        self.assertEqual(metrics["total_bytes"], 0)
        self.assertEqual(metrics["tier"], PeerTier.UNKNOWN.value)

    def test_record_transfer_and_tier_classification(self):
        now = time.time()
        # Record transfer resulting in low tier
        self.profiler.record_transfer(500, timestamp=now)
        bps = self.profiler.get_bandwidth_bps(current_time=now)
        self.assertGreater(bps, 0.0)
        self.assertEqual(self.profiler.get_tier(current_time=now), PeerTier.MEDIUM)

        # Record larger transfer to reach high tier
        self.profiler.record_transfer(10000, timestamp=now)
        self.assertEqual(self.profiler.get_tier(current_time=now), PeerTier.HIGH)

    def test_window_expiration(self):
        now = time.time()
        self.profiler.record_transfer(5000, timestamp=now)
        self.assertEqual(self.profiler.get_tier(current_time=now), PeerTier.HIGH)

        # Advance time beyond window
        future = now + 15.0
        self.assertEqual(self.profiler.get_bandwidth_bps(current_time=future), 0.0)
        self.assertEqual(self.profiler.get_tier(current_time=future), PeerTier.UNKNOWN)

    def test_reset(self):
        self.profiler.record_transfer(1000)
        self.profiler.reset()
        self.assertEqual(self.profiler.get_bandwidth_bps(), 0.0)
        self.assertEqual(self.profiler.get_tier(), PeerTier.UNKNOWN)
        self.assertEqual(self.profiler.get_metrics()["total_samples"], 0)


class TestPeerTierManager(unittest.TestCase):
    def setUp(self):
        self.config = BandwidthConfig(
            alpha=0.5,
            window_seconds=10.0,
            high_tier_threshold_bps=1000.0,
            medium_tier_threshold_bps=100.0,
        )
        self.manager = PeerTierManager(self.config)

    def test_manager_peer_operations(self):
        peer_id = "peer-node-alpha"
        self.assertEqual(self.manager.get_peer_tier(peer_id), PeerTier.UNKNOWN)

        self.manager.record_peer_transfer(peer_id, 5000)
        self.assertEqual(self.manager.get_peer_tier(peer_id), PeerTier.HIGH)

        all_metrics = self.manager.get_all_metrics()
        self.assertIn(peer_id, all_metrics)
        self.assertEqual(all_metrics[peer_id]["tier"], PeerTier.HIGH.value)

        self.manager.remove_peer(peer_id)
        self.assertEqual(self.manager.get_peer_tier(peer_id), PeerTier.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
