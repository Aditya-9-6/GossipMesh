import unittest
from gossipmesh.p2p.digest import HyperLogLogDigest, BloomFilterDigest


class TestHyperLogLogDigest(unittest.TestCase):
    def test_hll_cardinality_estimation(self):
        hll = HyperLogLogDigest(precision=10)
        num_items = 5000
        for i in range(num_items):
            hll.add(f"agent-node-{i}")

        est = hll.cardinality
        error = abs(est - num_items) / num_items
        # HLL error with precision 10 is approx 1.04 / sqrt(1024) approx 3.25%, but usually much closer.
        # We verify error is well within bounded operational limits (< 5% for p=10)
        self.assertLess(error, 0.05)

    def test_hll_serialization_and_deserialization(self):
        hll = HyperLogLogDigest(precision=8)
        for i in range(100):
            hll.add(f"item-{i}")

        payload = hll.serialize()
        self.assertIn("registers", payload)
        self.assertEqual(payload["precision"], 8)

        restored = HyperLogLogDigest.deserialize(payload)
        self.assertEqual(restored.precision, 8)
        self.assertAlmostEqual(restored.cardinality, hll.cardinality, delta=1.0)

    def test_hll_merge(self):
        hll1 = HyperLogLogDigest(precision=10)
        hll2 = HyperLogLogDigest(precision=10)

        for i in range(500):
            hll1.add(f"node-a-{i}")
        for i in range(500):
            hll2.add(f"node-b-{i}")

        hll1.merge(hll2)
        # Union should be around 1000 items
        est = hll1.cardinality
        error = abs(est - 1000) / 1000
        self.assertLess(error, 0.08)


class TestBloomFilterDigest(unittest.TestCase):
    def test_bloom_basic(self):
        bf = BloomFilterDigest(capacity=100, error_rate=0.01)
        bf.add("test-key")
        self.assertIn("test-key", bf)
        self.assertNotIn("missing-key", bf)

        ser = bf.serialize()
        des = BloomFilterDigest.deserialize(ser)
        self.assertIn("test-key", des)


if __name__ == "__main__":
    unittest.main()
