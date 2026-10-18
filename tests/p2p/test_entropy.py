import unittest
from gossipmesh.p2p.entropy import (
    VectorClockRingBuffer,
    compute_divergence_vector,
    compute_shannon_entropy,
    AntiEntropyScraper,
)


class TestAntiEntropyEntropy(unittest.TestCase):

    def test_ring_buffer_bounds(self):
        buf = VectorClockRingBuffer(capacity=3)
        buf.push({"nodeA": 1})
        buf.push({"nodeA": 2})
        buf.push({"nodeA": 3})
        buf.push({"nodeA": 4})
        
        items = buf.get_all()
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0], {"nodeA": 2})
        self.assertEqual(items[2], {"nodeA": 4})

    def test_compute_divergence_vector(self):
        local = {"nodeA": 5, "nodeB": 2}
        peer = {"nodeA": 2, "nodeC": 4}
        
        div = compute_divergence_vector(local, peer)
        self.assertEqual(div["nodeA"], 3)
        self.assertEqual(div["nodeB"], 2)
        self.assertEqual(div["nodeC"], 4)

    def test_compute_shannon_entropy(self):
        # Zero or empty divergence
        self.assertEqual(compute_shannon_entropy({}), 0.0)
        self.assertEqual(compute_shannon_entropy({"nodeA": 0}), 0.0)

        # Uniform distribution should have max entropy
        div = {"nodeA": 10, "nodeB": 10}
        entropy = compute_shannon_entropy(div)
        self.assertAlmostEqual(entropy, 1.0, places=4)

    def test_anti_entropy_scraper_evaluation(self):
        scraper = AntiEntropyScraper(entropy_threshold=1.0, buffer_capacity=10)
        
        local_clock = {"nodeA": 10, "nodeB": 10}
        # Highly divergent peer clock
        peer_clock = {"nodeA": 2, "nodeB": 18}
        
        scraper.record_peer_clock("peer-1", peer_clock)
        entropy, should_sync = scraper.evaluate_peer(local_clock, "peer-1")
        
        self.assertGreaterEqual(entropy, 1.0)
        self.assertTrue(should_sync)

    def test_anti_entropy_scraper_scan_mesh(self):
        scraper = AntiEntropyScraper(entropy_threshold=1.5, buffer_capacity=10)
        local_clock = {"nodeA": 10}
        
        scraper.record_peer_clock("peer-synced", {"nodeA": 10})
        scraper.record_peer_clock("peer-divergent", {"nodeA": 0, "nodeB": 50, "nodeC": 30})
        
        sync_peers = scraper.scan_mesh(local_clock)
        self.assertIn("peer-divergent", sync_peers)
        self.assertNotIn("peer-synced", sync_peers)


if __name__ == "__main പ്രധാന__":
    unittest.main()
