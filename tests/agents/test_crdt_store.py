import pytest
from gossipmesh.agents.crdt_store import DeltaORSetStore
from gossipmesh.agents.task_allocator import AgentTaskAllocator
from gossipmesh.agents.tombstone_gc import TombstoneGarbageCollector


def test_delta_or_set_store_basic_operations():
    store1 = DeltaORSetStore(node_id="node-A")

    # Add item
    elem, delta_tags = store1.add("task-1:agent-1")
    assert elem == "task-1:agent-1"
    assert len(delta_tags) == 1
    assert "task-1:agent-1" in store1.read()

    # Remove item
    _, removed_tags = store1.remove("task-1:agent-1")
    assert removed_tags == delta_tags
    assert "task-1:agent-1" not in store1.read()


def test_delta_or_set_store_merge():
    storeA = DeltaORSetStore(node_id="node-A")
    storeB = DeltaORSetStore(node_id="node-B")

    # Node A adds task
    _, deltaA = storeA.add("task-1:agent-1")

    # Node B merges Node A's delta
    storeB.merge_delta(delta={"task-1:agent-1": deltaA})
    assert "task-1:agent-1" in storeB.read()

    # Concurrent remove on Node A, add on Node B (add wins over concurrent remove in OR-Set semantics)
    _, tombstonesA = storeA.remove("task-1:agent-1")
    _, deltaB = storeB.add("task-1:agent-1")

    # Merge A into B (B's new add should survive since it has a fresh tag not in tombstonesA)
    storeB.merge_delta(delta={}, tombstones={"task-1:agent-1": tombstonesA})
    # Wait, tombstonesA contains the old tag. B's new tag was generated after. So B's new tag survives.
    # Let's verify merge from B into A:
    storeA.merge_delta(delta={"task-1:agent-1": deltaB}, tombstones={})
    assert "task-1:agent-1" in storeA.read()


def test_agent_task_allocator():
    allocator = AgentTaskAllocator(node_id="node-A")
    assignment, delta = allocator.claim_task("task-42", "agent-99")
    assert assignment == "task-42:agent-99"
    assert "task-42:agent-99" in allocator.get_active_tasks()

    _, removed = allocator.release_task("task-42", "agent-99")
    assert "task-42:agent-99" not in allocator.get_active_tasks()


def test_tombstone_garbage_collector():
    store = DeltaORSetStore(node_id="node-A")
    _, delta = store.add("task-1:agent-1")
    _, tombstones = store.remove("task-1:agent-1")

    gc = TombstoneGarbageCollector(node_id="node-A", stability_threshold_ticks=5)
    current_clock = {"node-A": 10}
    peer_clocks = {"node-B": {"node-A": 10}}

    pruned = gc.gc_tombstones(tombstones, current_clock, peer_clocks)
    # Since counter (1) <= stable clock (10), it should be garbage collected
    assert len(pruned) == 0
