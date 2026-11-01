from __future__ import annotations

import pytest
from gossipmesh.p2p.minhash import MinHashSketch
from gossipmesh.p2p.registry import MinHashSketchRegistry


def test_minhash_sketch_similarity():
    sketch1 = MinHashSketch(num_perm=64)
    sketch2 = MinHashSketch(num_perm=64)

    tokens_a = ["agent_alpha", "agent_beta", "agent_gamma", "node_1"]
    tokens_b = ["agent_alpha", "agent_beta", "agent_delta", "node_2"]

    sketch1.update_batch(tokens_a)
    sketch2.update_batch(tokens_b)

    sim = sketch1.jaccard(sketch2)
    assert 0.0 <= sim <= 1.0

    # Identical sketches should have Jaccard similarity of 1.0
    sketch3 = MinHashSketch(num_perm=64)
    sketch3.update_batch(tokens_a)
    assert sketch1.jaccard(sketch3) == 1.0


def test_registry_deduplication():
    registry = MinHashSketchRegistry(num_perm=64, similarity_threshold=0.5)

    registry.register_peer("peer_1", ["route_a", "route_b", "route_c", "route_shared"])
    registry.register_peer("peer_2", ["route_a", "route_b", "route_c", "route_shared"])
    registry.register_peer("peer_3", ["completely", "different", "routes"])

    duplicates = registry.find_duplicates("peer_1")
    dup_ids = [d[0] for d in duplicates]

    assert "peer_2" in dup_ids
    assert "peer_3" not in dup_ids


def test_memory_pressure_downsampling():
    registry = MinHashSketchRegistry(num_perm=128, max_capacity=2)
    registry.register_peer("peer_a", ["t1", "t2"])
    registry.register_peer("peer_b", ["t3", "t4"])

    # Trigger capacity enforcement
    registry.register_peer("peer_c", ["t5", "t6"])

    assert registry.size() == 3
    assert registry.num_perm == 64
