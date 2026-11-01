from __future__ import annotations

import unittest
from gossipmesh.p2p.ring import ConsistentHashRing


class TestConsistentHashRing(unittest.TestCase):
    def test_ring_add_remove_peer(self):
        ring = ConsistentHashRing(vnodes_per_peer=16)
        self.assertIsNone(ring.get_peer("test_key"))

        ring.add_peer("node-1")
        ring.add_peer("node-2")
        self.assertIn(ring.get_peer("test_key"), ["node-1", "node-2"])

        ring.remove_peer("node-1")
        # Now all keys should map to node-2
        self.assertEqual(ring.get_peer("test_key"), "node-2")

    def test_replicas_distribution(self):
        ring = ConsistentHashRing(vnodes_per_peer=32)
        for i in range(5):
            ring.add_peer(f"peer-{i}")

        replicas = ring.get_replicas("some-distributed-key", count=3)
        self.assertEqual(len(replicas), 3)
        self.assertEqual(len(set(replicas)), 3)

    def test_empty_ring(self):
        ring = ConsistentHashRing()
        self.assertIsNone(ring.get_peer("foo"))
        self.assertEqual(ring.get_replicas("foo", count=3), [])


if __name__ == "__main__":
    unittest.main()
