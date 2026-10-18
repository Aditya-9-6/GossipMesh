import unittest
from gossipmesh.p2p.reconciliation import VectorClock, AntiEntropyEngine


class TestVectorClockReconciliation(unittest.TestCase):

    def test_vector_clock_increment_and_compare(self):
        vc1 = VectorClock("node-A")
        vc2 = VectorClock("node-B")

        c1 = vc1.increment()
        self.assertEqual(c1, {"node-A": 1})

        # node-B updates with node-A's clock
        vc2.update(c1)
        self.assertEqual(vc2.clock["node-A"], 1)

        # Compare relation
        self.assertEqual(vc1.compare(vc2.clock), "older")
        self.assertEqual(vc2.compare(vc1.clock), "newer")

    def test_concurrent_clocks(self):
        vc1 = VectorClock("node-A")
        vc2 = VectorClock("node-B")

        vc1.increment()
        vc2.increment()

        self.assertEqual(vc1.compare(vc2.clock), "concurrent")

    def test_vector_clock_pruning(self):
        vc = VectorClock("node-A", max_epochs=2)
        vc.clock = {"node-A": 1, "node-B": 5, "node-C": 10}
        vc.prune()

        # Should retain node-A and max_epochs=2 highest
        self.assertIn("node-A", vc.clock)
        self.assertLessEqual(len(vc.clock), 2)

    def test_anti_entropy_engine_sync(self):
        engine_a = AntiEntropyEngine("node-A")
        engine_b = AntiEntropyEngine("node-B")

        clock_a = engine_a.set_state("config", "v1")
        accepted = engine_b.receive_state("config", "v1", "node-A", clock_a)

        self.assertTrue(accepted)
        self.assertEqual(engine_b.get_state("config"), "v1")

        # Older state rejection test
        accepted_again = engine_a.receive_state("config", "v0", "node-B", {"node-B": 0})
        self.assertFalse(accepted_again)
        self.assertEqual(engine_a.get_state("config"), "v1")

    def test_garbage_collection(self):
        engine = AntiEntropyEngine("node-A")
        engine.set_state("temp_key", "data")
        removed = engine.gc_state(max_age_seconds=-1)
        self.assertEqual(removed, 1)
        self.assertIsNone(engine.get_state("temp_key"))


if __name__ == "__main__":
    unittest.main()
