import unittest
import time

from gossipmesh.p2p.connection_pool import (
    LeakyBucketConnectionPool,
    ConnectionPoolConfig,
    ConnectionPriority,
)
from gossipmesh.p2p.backpressure import BackpressureConfig, BackpressureState


class TestLeakyBucketConnectionPool(unittest.TestCase):
    """Unit tests for Leaky-Bucket Connection Pool Manager and Backpressure Eviction."""

    def test_basic_acquire_and_release(self):
        config = ConnectionPoolConfig(max_capacity=5)
        pool = LeakyBucketConnectionPool(config)

        self.assertTrue(pool.acquire("peer-1", "socket-1", ConnectionPriority.NORMAL))
        self.assertEqual(pool.size(), 1)

        conn = pool.get("peer-1")
        self.assertIsNotNone(conn)
        self.assertEqual(conn.peer_id, "peer-1")

        self.assertTrue(pool.release("peer-1"))
        self.assertEqual(pool.size(), 0)
        self.assertIsNone(pool.get("peer-1"))

    def test_capacity_lru_eviction(self):
        config = ConnectionPoolConfig(max_capacity=2)
        pool = LeakyBucketConnectionPool(config)

        self.assertTrue(pool.acquire("peer-1", "sock-1"))
        self.assertTrue(pool.acquire("peer-2", "sock-2"))
        self.assertEqual(pool.size(), 2)

        # Touch peer-1 so peer-2 becomes LRU
        pool.touch("peer-1")

        # Acquiring peer-3 should evict peer-2 (LRU)
        self.assertTrue(pool.acquire("peer-3", "sock-3"))
        self.assertEqual(pool.size(), 2)
        self.assertIsNotNone(pool.get("peer-1"))
        self.assertIsNone(pool.get("peer-2"))
        self.assertIsNotNone(pool.get("peer-3"))

    def test_backpressure_shedding(self):
        bp_config = BackpressureConfig(elevated_threshold=0.5, critical_threshold=0.8, shedding_threshold=0.95)
        config = ConnectionPoolConfig(max_capacity=4, backpressure_config=bp_config)
        pool = LeakyBucketConnectionPool(config)

        # Fill up to 3 connections (75% saturation, between elevated 0.5 and critical 0.8)
        self.assertTrue(pool.acquire("peer-1", "s1", ConnectionPriority.NORMAL))
        self.assertTrue(pool.acquire("peer-2", "s2", ConnectionPriority.NORMAL))
        self.assertTrue(pool.acquire("peer-3", "s3", ConnectionPriority.NORMAL))

        metrics = pool.get_metrics()
        self.assertEqual(metrics["active_connections"], 3)

        # Fill 4th connection (100% saturation >= critical 0.8)
        self.assertTrue(pool.acquire("peer-4", "s4", ConnectionPriority.NORMAL))

        # Now at capacity with critical backpressure active (> 85% or config critical threshold).
        # In critical state, new LOW priority connections should be dropped.
        # Let's adjust capacity limit check or test drop behavior
        # With max_capacity=4 and 4 active, capacity is reached.
        # Trying to acquire a LOW priority connection under critical saturation will be dropped.
        success = pool.acquire("peer-5", "s5", ConnectionPriority.LOW)
        self.assertFalse(success)
        metrics = pool.get_metrics()
        self.assertEqual(metrics["dropped_total"], 1)

    def test_leaky_bucket_drain(self):
        config = ConnectionPoolConfig(max_capacity=5, leak_rate=2.0)
        pool = LeakyBucketConnectionPool(config)

        pool.acquire("p1", "s1")
        pool.acquire("p2", "s2")
        pool.acquire("p3", "s3")
        self.assertEqual(pool.size(), 3)

        evicted = pool.leak(2)
        self.assertEqual(len(evicted), 2)
        self.assertEqual(pool.size(), 1)
        self.assertEqual(evicted, ["p1", "p2"])

    def test_clear_pool(self):
        config = ConnectionPoolConfig(max_capacity=3)
        pool = LeakyBucketConnectionPool(config)
        pool.acquire("p1", "s1")
        pool.acquire("p2", "s2")
        self.assertEqual(pool.size(), 2)

        pool.clear()
        self.assertEqual(pool.size(), 0)
        metrics = pool.get_metrics()
        self.assertEqual(metrics["active_connections"], 0)
        self.assertEqual(metrics["allocated_total"], 0)
        self.assertEqual(metrics["dropped_total"], 0)


if __name__ == "__main覚えて__":
    unittest.main()
