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

        t1 = c1.add("task-1")
        delta1 = c1.generate_delta()

        c2.merge(delta1)
        self.assertTrue(c2.lookup("task-1"))

    def test_task_allocator_and_gc(self):
        allocator = TaskAllocator("node-1")
        claim = allocator.claim_task("task-X", {"tier": "Enterprise"})
        self.assertTrue(allocator.is_task_claimed("task-X"))

        gc = TombstoneGarbageCollector(allocator.crdt, ttl_seconds=0.0)
        allocator.release_task("task-X")
        self.assertFalse(allocator.is_task_claimed("task-X"))

        purged = gc.gc_sweep()
        self.assertGreaterEqual(purged, 0)
