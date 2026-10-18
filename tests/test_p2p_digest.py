import unittest
from gossipmesh.p2p.digest import HyperLogLogDigest

class TestHyperLogLogDigest(unittest.TestCase):
    def test_init_validation(self):
        with self.assertRaises(ValueError):
            HyperLogLogDigest(precision=3)
        with self.assertRaises(ValueError):
            HyperLogLogDigest(precision=17)

    def test_cardinality_estimation(self):
        hll = HyperLogLogDigest(precision=12)
        items = [f"msg-{i}" for i in range(1000)]
        for item in items:
            hll.add(item)
        
        estimate = hll.estimate_cardinality()
        error = abs(estimate - 1000) / 1000.0
        self.assertLess(error, 0.05, f"Error {error} exceeds tolerance")

    def test_merge_and_serialization(self):
        hll1 = HyperLogLogDigest(precision=10)
        hll2 = HyperLogLogDigest(precision=10)

        for i in range(500):
            hll1.add(f"item-{i}")
        for i in range(500, 1000):
            hll2.add(f"item-{i}")

        merged = hll1.merge(hll2)
        estimate = merged.estimate_cardinality()
        error = abs(estimate - 1000) / 1000.0
        self.assertLess(error, 0.10)

        serialized = hll1.serialize()
        deserialized = HyperLogLogDigest.deserialize(serialized)
        self.assertEqual(hll1.registers, deserialized.registers)

    def test_precision_mismatch_merge(self):
        hll1 = HyperLogLogDigest(precision=10)
        hll2 = HyperLogLogDigest(precision=12)
        with self.assertRaises(ValueError):
            hll1.merge(hll2)

if __name__ == '__main__':
    unittest.main()
