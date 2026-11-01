"""Unit tests for GossipMesh SHA-256 Merkle-DAG State Reconciler."""

import pytest
from gossipmesh.core.merkle import MerkleDAG, MerkleNode, hash_leaf, hash_nodes


def test_hash_primitives():
    h1 = hash_leaf("agent_status", "active")
    h2 = hash_leaf("agent_status", "active")
    h3 = hash_leaf("agent_status", "idle")

    assert h1 == h2
    assert h1 != h3

    combined = hash_nodes(h1, h3)
    assert isinstance(combined, str)
    assert len(combined) == 64


def test_merkle_dag_identical_states():
    state_a = {"agent:1": {"status": "running"}, "agent:2": {"status": "idle"}}
    state_b = {"agent:1": {"status": "running"}, "agent:2": {"status": "idle"}}

    dag_a = MerkleDAG(state_a)
    dag_b = MerkleDAG(state_b)

    assert dag_a.root_hash == dag_b.root_hash
    divergences = dag_a.find_divergences(dag_b.root)
    assert divergences == []


def test_merkle_dag_divergent_states():
    state_a = {"agent:1": {"status": "running"}, "agent:2": {"status": "idle"}}
    state_b = {"agent:1": {"status": "stopped"}, "agent:2": {"status": "idle"}}

    dag_a = MerkleDAG(state_a)
    dag_b = MerkleDAG(state_b)

    assert dag_a.root_hash != dag_b.root_hash
    divergences = dag_a.find_divergences(dag_b.root)
    assert divergences == ["agent:1"]


def test_merkle_dag_multiple_divergences():
    state_a = {"a": 1, "b": 2, "c": 3, "d": 4}
    state_b = {"a": 1, "b": 99, "c": 3, "d": 88}

    dag_a = MerkleDAG(state_a)
    dag_b = MerkleDAG(state_b)

    divergences = dag_a.find_divergences(dag_b.root)
    assert divergences == ["b", "d"]


def test_empty_merkle_dag():
    dag_empty = MerkleDAG({})
    dag_populated = MerkleDAG({"x": 10})

    assert dag_empty.root_hash != dag_populated.root_hash
    assert dag_empty.find_divergences(dag_populated.root) == ["x"]


def test_inclusion_proof():
    state = {"alpha": 100, "beta": 200, "gamma": 300}
    dag = MerkleDAG(state)

    proof = dag.get_proof("beta")
    assert isinstance(proof, list)
    assert len(proof) > 0
    for item in proof:
        assert "sibling_hash" in item
        assert "position" in item
