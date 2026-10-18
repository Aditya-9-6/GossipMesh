import unittest
from gossipmesh.core.clocks import VectorClock

class TestVectorClock(unittest.TestCase):
    def test_initialization(self):
        vc = VectorClock("node-A")
        self.assertEqual(vc.snapshot(), {"node-A": 0})
        self.assertEqual(vc.get_time("node-A"), 0)

    def test_increment(self):
        vc = VectorClock("node-A")
        self.assertEqual(vc.increment(), 1)
        self.assertEqual(vc.increment(), 2)
        self.assertEqual(vc.snapshot(), {"node-A": 2})

    def test_update_and_comparison(self):
        vc1 = VectorClock("node-A", {"node-A": 2, "node-B": 1})
        vc2 = VectorClock("node-B", {"node-A": 1, "node-B": 3})

        self.assertEqual(vc1.compare(vc2.snapshot()), "CONCURRENT")

        vc1.update({"node-B": 5})
        self.assertEqual(vc1.compare(vc2.snapshot()), "GREATER_THAN")
        self.assertEqual(vc2.compare(vc1.snapshot()), "LESS_THAN")

    def test_delta(self):
        vc = VectorClock("node-A", {"node-A": 5, "node-B": 3, "node-C": 2})
        peer_clock = {"node-A": 3, "node-B": 3, "node-D": 1}

        d = vc.delta(peer_clock)
        # node-A (5 > 3 -> included), node-B (3 > 3 -> excluded), node-C (2 > 0 -> included)
        self.assertEqual(d, {"node-A": 5, "node-C": 2})

    def test_equal_comparison(self):
        vc1 = VectorClock("node-A", {"node-A": 1, "node-B": 2})
        vc2 = VectorClock("node-B", {"node-A": 1, "node-B": 2})
        self.assertEqual(vc1.compare(vc2.snapshot()), "EQUAL")

if __name__ == "__main":
    unittest.main()
