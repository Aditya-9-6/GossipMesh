import pytest
import asyncio
from gossipmesh.p2p.entropy import (
    VectorClockRingBuffer,
    VectorClockEntropy,
    AntiEntropyEntropy,
    compute_divergence_vector,
    compute_shannon_entropy,
    HierarchicalAntiEntropySyncer,
)
from gossipmesh.p2p.merkle import MerkleDAG


def test_vector_clock_ring_buffer():
    buf = VectorClockRingBuffer(capacity=2)
    buf.push({"node1": 1})
    buf.push({"node1": 2})
    buf.push({"node1": 3})

    all_clocks = buf.get_all()
    assert len(all_clocks) == 2
    assert all_clocks[0] == {"node1": 2}
    assert all_clocks[1] == {"node1": 3}


def test_shannon_entropy_calculation():
    div_vec = {"n1": 5, "n2": 5}
    entropy = compute_shannon_entropy(div_vec)
    assert entropy == 1.0

    empty_vec = {}
    assert compute_shannon_entropy(empty_vec) == 0.0


def test_anti_entropy_evaluation():
    ae = AntiEntropyEntropy(threshold=0.5)
    local = {"n1": 10, "n2": 0}
    peer = {"n1": 0, "n2": 10}
    assert ae.evaluate(local, peer) is True


@pytest.mark.asyncio
async def test_hierarchical_anti_entropy_syncer():
    local_state = {"task:1": "completed", "task:2": "pending"}
    remote_state = {"task:1": "completed", "task:2": "failed"}

    remote_dag = MerkleDAG(remote_state)
    syncer = HierarchicalAntiEntropySyncer(node_id="node-local", state_store=local_state, latency_budget_ms=50.0)

    divergences = await syncer.reconcile_with_peer("node-remote", remote_dag.root)
    assert divergences == ["task:2"]
