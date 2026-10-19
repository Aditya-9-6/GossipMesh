import unittest
import threading
from gossipmesh.p2p.dedup import GossipDedupFilter


class TestGossipDedupFilter(unittest.TestCase):
    def test_initialization_validation(self):
        """Tests initialization with invalid capacity."""
        with self.assertRaises(ValueError):
            GossipDedupFilter(capacity=0)
        with self.assertRaises(ValueError):
            GossipDedupFilter(capacity=-5)

    def test_basic_deduplication(self):
        """Tests basic frame insertion and duplicate detection."""
        dedup = GossipDedupFilter(capacity=100)
        frame1 = b"gossip_payload_alpha"
        frame2 = b"gossip_payload_beta"

        # First time seeing frames -> should not be duplicate (returns False)
        self.assertFalse(dedup.check_and_add(frame1))
        self.assertFalse(dedup.check_and_add(frame2))

        # Second time seeing frames -> should be duplicate (returns True)
        self.assertTrue(dedup.check_and_add(frame1))
        self.assertTrue(dedup.check_and_add(frame2))

        metrics = dedup.get_metrics()
        self.assertEqual(metrics["current_size"], 2)
        self.assertEqual(metrics["total_evaluated"], 4)
        self.assertEqual(metrics["duplicates_filtered"], 2)
        self.assertAlmostEqual(metrics["hit_ratio"], 0.5)

    def test_ring_buffer_capacity_eviction(self):
        """Tests that the ring buffer evicts oldest elements correctly when exceeding capacity."""
        capacity = 3
        dedup = GossipDedupFilter(capacity=capacity)

        f1 = b"frame_1"
        f2 = b"frame_2"
        f3 = b"frame_3"
        f4 = b"frame_4"

        # Fill capacity
        self.assertFalse(dedup.check_and_add(f1))
        self.assertFalse(dedup.check_and_add(f2))
        self.assertFalse(dedup.check_and_add(f3))
        self.assertEqual(dedup.get_metrics()["current_size"], 3)

        # f1 should still be present
        self.assertTrue(dedup.is_duplicate(f1))

        # Add f4, which should evict f1
        self.assertFalse(dedup.check_and_add(f4))

        # f1 should now be evicted and treated as new
        self.assertFalse(dedup.check_and_add(f1))

        # f2 should now be evicted (since capacity is 3 and we added f1, f3, f4, f1)
        self.assertTrue(dedup.is_duplicate(f3))
        self.assertTrue(dedup.is_duplicate(f4))
        self.assertTrue(dedup.is_duplicate(f1))

    def test_clear_filter(self):
        """Tests resetting the filter state."""
        dedup = GossipDedupFilter(capacity=10)
        frame = b"test_frame"
        self.assertFalse(dedup.check_and_add(frame))
        self.assertTrue(dedup.is_duplicate(frame))

        dedup.clear()
        metrics = dedup.get_metrics()
        self.assertEqual(metrics["current_size"], 0)
        self.assertEqual(metrics["total_evaluated"], 0)
        self.assertFalse(dedup.is_duplicate(frame))
        self.assertFalse(dedup.check_and_add(frame))

    def test_concurrent_access(self):
        """Tests thread-safety under concurrent multi-threaded evaluation."""
        dedup = GossipDedupFilter(capacity=1000)
        num_threads = 10
        iterations_per_thread = 100

        def worker(thread_id: int):
            for i in range(iterations_per_thread):
                frame = f"frame_{thread_id}_{i}".encode()
                dedup.check_and_add(frame)
                # Evaluate duplicate again immediately
                dedup.check_and_add(frame)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        metrics = dedup.get_metrics()
        expected_evaluations = num_threads * iterations_per_thread * 2
        expected_duplicates = num_threads * iterations_per_thread
        self.assertEqual(metrics["total_evaluated"], expected_evaluations)
        self.assertEqual(metrics["duplicates_filtered"], expected_duplicates)


if __name__ == "__main__":
    unittest.main()
