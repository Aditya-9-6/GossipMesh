import threading
import unittest
from gossipmesh.core.clocks import VectorClock


class TestVectorClock(unittest.TestCase):
    def test_initialization_and_snapshot(self):
        vc = VectorClock("node-A", {"node-A": 5, "node-B": 2})
        self.assertEqual(vc.node_id, "node-A")
        self.assertEqual(vc.snapshot(), {"node-A": 5, "node-B": 2})

    def test_default_initialization(self):
        vc = VectorClock("node-A")
        self.assertEqual(vc.snapshot(), {"node-A": 0})

    def test_increment(self):
        vc = VectorClock("node-A")
        self.assertEqual(vc.increment(), 1)
        self.assertEqual(vc.increment(), 2)
        self.assertEqual(vc.get_time("node-A"), 2)

    def test_update(self):
        vc = VectorClock("node-A", {"node-A": 1})
        vc.update({"node-A": 3, "node-B": 4, "node-C": 2})
        self.assertEqual(vc.snapshot(), {"node-A": 3, "node-B": 4, "node-C": 2})

    def test_delta_and_iter_delta(self):
        vc = VectorClock("node-A", {"node-A": 5, "node-B": 3, "node-C": 1})
        known = {"node-A": 3, "node-B": 3, "node-D": 1}

        d = vc.delta(known)
        self.assertEqual(d, {"node-A": 5, "node-C": 1})

        iter_res = dict(vc.iter_delta(known))
        self.assertEqual(iter_res, {"node-A": 5, "node-C": 1})

    def test_compare_relations(self):
        vc1 = VectorClock("node-A", {"node-A": 2, "node-B": 1})

        # EQUAL
        self.assertEqual(vc1.compare({"node-A": 2, "node-B": 1}), "EQUAL")

        # GREATER_THAN
        self.assertEqual(vc1.compare({"node-A": 1, "node-B": 1}), "GREATER_THAN")
        self.assertEqual(vc1.compare({"node-A": 2, "node-B": 0}), "GREATER_THAN")

        # LESS_THAN
        self.assertEqual(vc1.compare({"node-A": 3, "node-B": 2}), "LESS_THAN")

        # CONCURRENT
        vc2 = VectorClock("node-B", {"node-A": 1, "node-B": 3})
        self.assertEqual(vc1.compare(vc2.snapshot()), "CONCURRENT")

    def test_thread_safety(self):
        vc = VectorClock("node-A")
        threads = []

        def worker():
            for _ in range(100):
                vc.increment()
                vc.update({"node-B": 1})

        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertGreaterEqual(vc.get_time("node-A"), 100)
        self.assertEqual(vc.get_time("node-B"), 1)


if __name__ == "__main休日__":
    unittest.main()
