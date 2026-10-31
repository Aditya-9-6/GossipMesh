import pytest
from gossipmesh.agents.crdt_store import DeltaORSetStore
from gossipmesh.agents.task_allocator import AgentTaskAllocator
from gossipmesh.agents.tombstone_gc import TombstoneGarbageCollector


def test_delta_orset_basic_add_remove():
    store1 = DeltaORSetStore(node_id="node-1")
    
    # Add element
    elem, delta1 = store1.add("task_a:agent_1")
    assert elem == "task_a:agent_1"
    assert len(delta1) == 1
    assert "task_a:agent_1" in store1.read()

    # Remove element
    _, removed_tags = store1.remove("task_a:agent_1")
    assert "task_a:agent_1" not in store1.read()


def test_crdt_concurrent_merge_join_semilattice():
    store1 = DeltaORSetStore(node_id="node-1")
    store2 = DeltaORSetStore(node_id="node-2")

    # Node 1 claims task A
    _, delta1 = store1.add("task_a:agent_1")
    # Node 2 claims task B
    _, delta2 = store2.add(
        "task_b:agent_2"
    )

    # Cross merge deltas
    store1.merge_delta(delta2)
    store2.merge_delta(delta1)

    assert "task_a:agent_1" in store1.read()
    assert "task_b:agent_2" in store1.read()
    assert "task_a:agent_1" in store2.read()
    assert "task_b:agent_2" in store2.read()


def test_crdt_add_wins_concurrent_remove():
    store1 = DeltaORSetStore(node_id="node-1")
    store2 = DeltaORSetStore(node_id="node-2")

    # Node 1 adds task
    _, delta1 = store1.add("task_x:agent_x")
    
    # Node 2 merges delta1 so both have task_x
    store2.merge_delta(delta1)
    assert "task_x:agent_x" in store2.read()

    # Concurrently, Node 1 removes task_x while Node 2 concurrently adds a fresh tag for task_x
    _, tombstones1 = store1.remove("task_x:agent_x")
    _, delta2_fresh = store2.add("task_x:agent_x")

    # Merge store1's remove into store2, and store2's new add into store1
    store2.merge_delta({}, tombstones1)
    store1.merge_delta(delta2_fresh)

    # Add wins semantic: the concurrent add should survive the remove
    assert "task_x:agent_x" in store2.read()
    assert "task_x:agent_x" in store1.read()


def test_task_allocator_and_gc():
    allocator = AgentTaskAllocator(node_id="node-1")
    assignment, delta = allocator.claim_task("task_100", "agent_alpha")
    assert assignment == "task_100:agent_alpha"
    assert "task_100:agent_alpha" in allocator.get_active_tasks()

    gc = TombstoneGarbageCollector(node_id="node-1")
    _, tombstones = allocator.release_task("task_100", "agent_alpha")
    
    elements, current_tombstones = allocator.store.get_full_state()
    pruned = gc.gc_tombstones(current_tombstones, allocator.vector_clock.snapshot(), {"node-2": {"node-2": 5}})
    assert isinstance(pruned, dict)
