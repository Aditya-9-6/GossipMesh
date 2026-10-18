import unittest
import time
from gossipmesh.p2p.metrics import (
    PeerTier,
    BandwidthProfilerConfig,
    WindowedEWMABandwidthProfiler,
    PeerTierManager,
)


class TestWindowedEWMABandwidthProfiler(unittest.TestCase):
    def test_initial_state(self):
        profiler = WindowedEWMABandwidthProfiler()
        self.assertEqual(profiler.get_bandwidth_bps(), 0.0)
        self.assertEqual(profiler.get_tier(), PeerTier.LOW)
        metrics = profiler.get_metrics()
        self.assertEqual(metrics["active_samples"], 0)
        self.assertEqual(metrics["ewma_bps"], 0.0)

    def test_record_transfer_and_tiering(self):
        config = BandwidthProfilerConfig(
            window_size_seconds=60.0,
            high_tier_threshold_bps=1000.0,
            medium_tier_threshold_bps=100.0,
        )
        profiler = WindowedEWMABandwidthProfiler(config)
        now = time.time()

        # Record transfer resulting in low tier
        profiler.record_transfer(500, timestamp=now)
        self.assertGreater(profiler.get_bandwidth_bps(now), 0.0)
        self.assertEqual(profiler.get_tier(now), PeerTier.MEDIUM)

        # Record more transfers to hit HIGH tier
        profiler.record_transfer(100000, timestamp=now + 1.0)
        self.assertEqual(profiler.get_tier(now + 1.0), PeerTier.HIGH)

    def test_sample_pruning(self):
        config = BandwidthProfilerConfig(window_size_seconds=10.0)
        profiler = WindowedEWMABandwidthProfiler(config)
        now = time.time()

        profiler.record_transfer(5000, timestamp=now)
        self.assertEqual(profiler.get_metrics(now)["active_samples"], 1)

        # Advance time beyond window size
        future = now + 15.0
        self.assertEqual(profiler.get_bandwidth_bps(future), 0.0)
        self.assertEqual(profiler.get_metrics(future)["active_samples"], 0)

    def test_reset(self):
        profiler = WindowedEWMABandwidthProfiler()
        profiler.record_transfer(1000)
        self.assertGreater(profiler.get_bandwidth_bps(), 0.0)
        profiler.reset()
        self.assertEqual(profiler.get_bandwidth_bps(), 0.0)
        self.assertEqual(profiler.get_metrics()["active_samples"], 0)


class TestPeerTierManager(unittest.TestCase):
    def test_peer_tier_manager_lifecycle(self):
        manager = PeerTierManager()
        peer_id = "peer-alpha"

        self.assertEqual(manager.get_peer_tier(peer_id), PeerTier.UNKNOWN)

        manager.record_peer_transfer(peer_id, 2_000_000)
        self.assertEqual(manager.get_peer_tier(peer_id), PeerTier.HIGH)

        all_metrics = manager.get_all_metrics()
        self.assertIn(peer_id, all_metrics)
        self.assertEqual(all_metrics[peer_id]["tier"], PeerTier.HIGH.value)

        manager.remove_peer(peer_id)
        self.assertEqual(manager.get_peer_tier(peer_id), PeerTier.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
