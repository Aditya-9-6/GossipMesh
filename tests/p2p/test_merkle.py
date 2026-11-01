import pytest
from gossipmesh.p2p.merkle import MerkleDAG, MerkleNode, hash_leaf, hash_nodes


def test_merkle_dag_empty():
    dag = MerkleDAG({})
    assert dag.root_hash is not None
    assert len(dag.root_hash) > 0


def test_merkle_dag_single_item():
    state = {"agent:1": "active"}
    dag = MerkleDAG(state)
    assert dag.root is not None
    assert dag.root.is_leaf
    assert dag.root.key == "agent:1"


def test_merkle_dag_divergence_detection():
    state_a = {"k1": "v1", "k2": "v2", "k3": "v3"}
    state_b = {"k1": "v1", "k2": "v2_divergent", "k3": "v3"}

    dag_a = MerkleDAG(state_a)
    dag_b = MerkleDAG(state_b)

    divergences = dag_a.find_divergences(dag_b.root)
    assert divergences == ["k2"]


def test_merkle_dag_multiple_divergences():
    state_a = {"a": 1, "b": 2, "c": 3, "d": 4}
    state_b = {"a": 99, "b": 2, "c": 99, "d": 4}

    dag_a = MerkleDAG(state_a)
    dag_b = MerkleDAG(state_b)

    divergences = dag_a.find_divergences(dag_b.root)
    assert sorted(divergences) == ["a", "c"]
