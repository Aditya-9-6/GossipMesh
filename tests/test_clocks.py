import unittest
import threading
from gossipmesh.core.clocks import VectorClock


class TestVectorClock(unittest.TestCase):

    def test_initialization_and_increment(self):
        vc = VectorClock("node-A")
        self.assertEqual(vc.get_time("node-A"), 0)
        
        new_time = vc.increment()
        self.assertEqual(new_time, 1)
        self.assertEqual(vc.get_time("node-A"), 1)

    def test_update_and_snapshot(self):
        vc = VectorClock("node-A", {"node-A": 2, "node-B": 1})
        vc.update({"node-B": 3, "node-C": 5})
        snap = vc.snapshot()
        
        self.assertEqual(snap, {"node-A": 2, "node-B": 3, "node-C": 5})

    def test_delta_and_iter_delta(self):
        vc = VectorClock("node-A", {"node-A": 5, "node-B": 4, "node-C": 2})
        known = {"node-A": 3, "node-B": 4}
        
        d = vc.delta(known)
        self.assertEqual(d, {"node-A": 5, "node-C": 2})

        generator_results = dict(vc.iter_delta(known))
        self.assertEqual(generator_results, {"node-A": 5, "node-C": 2})

    def test_update_from_delta(self):
        vc = VectorClock("node-A", {"node-A": 1})
        vc.update_from_delta({"node-B": 4, "node-A": 2})
        self.assertEqual(vc.snapshot(), {"node-A": 2, "node-B": 4})

    def test_comparisons(self):
        vc = VectorClock("node-A", {"node-A": 2, "node-B": 2})
        
        # EQUAL
        self.assertEqual(vc.compare({"node-A": 2, "node-B": 2}), "EQUAL")
        
        # GREATER_THAN
        self.assertEqual(vc.compare({"node-A": 1, "node-B": 2}), "GREATER_THAN")
        self.assertEqual(vc.compare({"node-A": 2, "node-B": 1}), "GREATER_THAN")
        
        # LESS_THAN
        self.assertEqual(vc.compare({"node-A": 3, "node-B": 3}), "LESS_THAN")
        
        # CONCURRENT
        self.assertEqual(vc.compare({"node-A": 3, "node-B": 1}), "CONCURRENT")
        self.assertEqual(vc.compare({"node-C": 1}), "CONCURRENT")

    def test_thread_safety(self):
        vc = VectorClock("node-A", {"node-A": 0})
        threads = []

        def worker():
            for _ in range(100):
                vc.increment()
                vc.update({"node-B": 5})

        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(vc.get_time("node-A"), 1000)
        self.assertEqual(vc.get_time("node-B"), 5)


if __name__ == "__main__":
    unittest.main()
