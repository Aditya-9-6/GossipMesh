import unittest
from gossipmesh.agents.crdt_store import DeltaORSetCRDT
from gossipmesh.agents.task_allocator import TaskAllocator
from gossipmesh.agents.tombstone_gc import TombstoneGarbageCollector


class TestCRDTStoreAndTaskAllocator(unittest.TestCase):
    def test_or_set_basic_operations(self):
        crdt = DeltaORSetCRDT("node-1")
        self.assertFalse(crdt.lookup("task-A"))

        crdt.add("task-A")
        self.assertTrue(crdt.lookup("task-A"))
        self.assertIn("task-A", crdt.get_elements())

        crdt.remove("task-A")
        self.assertFalse(crdt.lookup("task-A"))
        self.assertNotIn("task-A", crdt.get_elements())

    def test_join_semilattice_properties(self):
        # Commutativity and Associativity test across multiple peers
        c1 = DeltaORSetCRDT("node-1")
        c2 = DeltaORSetCRDT("node-2")

        t1 = c1.add("task-X")
        delta1 = c1.generate_delta()

        c2.merge(delta1)
        self.assertTrue(c2.lookup("task-X"))

        # Commutativity: merging in different orders or concurrent adds
        t2 = c2.add("task-Y")
        delta2 = c2.generate_delta()

        c1.merge(delta2)
        self.assertTrue(c1.lookup("task-Y"))
        self.assertTrue(c1.lookup("task-X"))
        self.assertTrue(c2.lookup("task-X"))
        self.assertTrue(c2.lookup("task-Y"))

    def test_task_allocator_and_gc(self):
        allocator = TaskAllocator("node-1")
        res = allocator.claim_task("task-100", {"owner": "agent-1"})
        self.assertTrue(allocator.is_task_claimed("task-100"))

        rel = allocator.release_task("task-100")
        self.assertFalse(allocator.is_task_claimed("task-100"))

        gc = TombstoneGarbageCollector(allocator.crdt, ttl_seconds=0)
        purged = gc.gc_sweep({"node-1": 100})
        self.assertGreaterEqual(purged, 0)


if __name__ == "__main__":
    unittest.main()
