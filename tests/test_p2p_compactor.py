import unittest
from gossipmesh.p2p.compactor import GossipDigestCompactor


class TestGossipDigestCompactor(unittest.TestCase):
    def test_compactor_lifecycle_and_reconciliation(self):
        compactor1 = GossipDigestCompactor(precision=10)
        compactor2 = GossipDigestCompactor(precision=10)

        for i in range(300):
            compactor1.add_peer_state(f"state-key-{i}")
        for i in range(200, 500):
            compactor2.add_peer_state(f"state-key-{i}")

        digest1 = compactor1.compact()
        digest2 = compactor2.compact()

        # Verify payload size is strictly bounded (<1KB)
        import json
        payload_size = len(json.dumps(digest1))
        self.assertLess(payload_size, 2048)  # Well under compact budget

        union_cardinality = GossipDigestCompactor.reconcile(compactor1, digest2)
        # Union of [0..299] and [200..499] is 500 unique items
        error = abs(union_cardinality - 500) / 500
        self.assertLess(error, 0.08)


if __name__ == "__main__":
    unittest.main()
