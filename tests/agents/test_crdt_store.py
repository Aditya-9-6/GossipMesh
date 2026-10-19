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
        store_a = DeltaORSetCRDT("node-A")
        store_b = DeltaORSetCRDT("node-B")

        store_a.add("task-1")
        delta_a = store_a.generate_delta()

        store_b.add("task-2")
        delta_b = store_b.generate_delta()

        # Merge A into B, then B into A should produce equivalent final state
        store_a_copy = DeltaORSetCRDT("node-A")
        store_a_copy.merge(delta_a)
        store_a_copy.merge(delta_b)

        store_b_copy = DeltaORSetCRDT("node-B")
        store_b_copy.merge(delta_b)
        store_b_copy.merge(delta_a)

        self.assertEqual(store_a_copy.get_elements(), store_b_copy.get_elements())
        self.assertEqual(store_a_copy.get_elements(), {"task-1", "task-2"})

    def test_task_allocator_workflow(self):
        allocator_1 = TaskAllocator("agent-1")
        allocator_2 = TaskAllocator("agent-2")

        claim_res = allocator_1.claim_task("task-refactor", {"repo": "gossipmesh"})
        self.assertTrue(allocator_1.is_task_claimed("task-refactor"))

        # Sync delta to allocator 2
        allocator_2.receive_delta(claim_res["delta"])
        self.assertTrue(allocator_2.is_task_claimed("task-refactor"))

        # Release task from allocator 1
        release_res = allocator_1.release_task("task-refactor")
        self.assertFalse(allocator_1.is_task_claimed("task-refactor"))

        # Sync release delta to allocator 2
        allocator_2.receive_delta(release_res["delta"])
        self.assertFalse(allocator_2.is_task_claimed("task-refactor"))

    def test_tombstone_garbage_collection(self):
        crdt = DeltaORSetCRDT("node-1")
        tag = crdt.add("task-gc")
        crdt.remove("task-gc")
        self.assertEqual(len(crdt.remove_set), 1)

        gc = TombstoneGarbageCollector(crdt, ttl_seconds=-1.0) # force immediate TTL expiration
        purged = gc.gc_sweep()
        self.assertEqual(purged, 1)
        self.assertEqual(len(crdt.remove_set), 0)

if __name__ == "__main মূল__":
    unittest.main()
