from __future__ import annotations

import pytest
from gossipmesh.p2p.ring import ConsistentHashRing


def test_consistent_hash_ring_basic():
    ring = ConsistentHashRing(vnodes_per_peer=16)
    assert ring.peer_count == 0
    assert ring.get_peer("test-key") is None

    ring.add_peer("node-1")
    ring.add_peer("node-2")
    assert ring.peer_count == 2
    assert ring.vnode_count == 32

    peer = ring.get_peer("my-agent-key")
    assert peer in ("node-1", "node-2")

    ring.remove_peer("node-1")
    assert ring.peer_count == 1
    assert ring.get_peer("my-agent-key") == "node-2"


def test_replicas_allocation():
    ring = ConsistentHashRing(vnodes_per_peer=8)
    for p in ["alpha", "beta", "gamma", "delta"]:
        ring.add_peer(p)

    replicas = ring.get_replicas(
        "distributed-workload-task", count=3
    )
    assert len(replicas) == 3
    assert len(set(replicas)) == 3
    for r in replicas:
        assert r in ("alpha", "beta", "gamma", "delta")


def test_uniform_distribution_variance():
    ring = ConsistentHashRing(vnodes_per_peer=64)
    nodes = [f"peer-{i}" for i in range(5)]
    for n in nodes:
        ring.add_peer(n)

    counts = {n: 0 for n in nodes}
    total_keys = 2000
    for i in range(total_keys):
        assigned = ring.get_peer(f"key-{i}")
        if assigned:
            counts[assigned] += 1

    expected = total_keys / len(nodes)
    # Check that no node deviates more than 50% from the expected mean
    for n, count in counts.items():
        assert abs(count - expected) < (expected * 0.5)


def test_bounded_load_rebalancing():
    ring = ConsistentHashRing(vnodes_per_peer=16)
    ring.add_peer("node-a")
    keys = [f"task-{i}" for i in range(100)]
    alloc, migrated = ring.rebalance_load(keys, max_migration_ratio=0.2)
    assert "node-a" in alloc
    assert len(alloc["node-a"]) == 100
    assert migrated == 0
