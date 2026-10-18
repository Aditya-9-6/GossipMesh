import unittest
from gossipmesh.p2p.compactor import GossipDigestCompactor
from gossipmesh.p2p.digest import HyperLogLogDigest

class TestGossipDigestCompactor(unittest.TestCase):
    def test_compact_and_diff(self):
        compactor = GossipDigestCompactor(precision=10)
        local_ids = [f"id-{i}" for i in range(500)]
        remote_ids = [f"id-{i}" for i in range(250, 750)]

        local_digest = compactor.compact_state(local_ids)
        remote_digest = compactor.compact_state(remote_ids)

        diff = compactor.compute_diff(local_digest, remote_digest)
        self.assertGreaterEqual(diff, 0.0)

    def test_serialization_roundtrip(self):
        compactor = GossipDigestCompactor(precision=10)
        digest = compactor.compact_state(["a", "b", "c"])
        serialized = compactor.serialize_digest(digest)
        deserialized = compactor.deserialize_digest(serialized)
        self.assertEqual(digest.registers, deserialized.registers)

if __name__ == '__main__':
    unittest.main()
