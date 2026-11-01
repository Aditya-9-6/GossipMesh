"""Unit tests for GossipDigestArena zero-copy SIMD-vectorized digest filtering."""

import pytest
import concurrent.futures
from gossipmesh.p2p.digest_arena import GossipDigestArena


def test_digest_arena_basic_operations():
    arena = GossipDigestArena(capacity=100, error_rate=0.01)
    assert arena.size == 0

    arena.add("agent_task_alpha")
    arena.add("agent_task_beta")

    assert "agent_task_alpha" in arena
    assert "agent_task_beta" in arena
    assert "agent_task_gamma" not in arena
    assert arena.size >= 2


def test_digest_arena_vectorized_batch_filter():
    arena = GossipDigestArena(capacity=500, error_rate=0.01)
    arena.add("id_1")
    arena.add(
        "id_3"
    )

    incoming = ["id_1", "id_2", "id_3", "id_4"]
    missing = arena.batch_filter_vectorized(incoming)

    assert "id_1" not in missing
    assert "id_3" not in missing
    assert "id_2" in missing
    assert "id_4" in missing


def test_digest_arena_serialization():
    arena = GossipDigestArena(capacity=200, error_rate=0.02)
    arena.add("sync_key_99")

    data = arena.serialize()
    restored = GossipDigestArena.deserialize(data)

    assert "sync_key_99" in restored
    assert restored.size == arena.size
    assert "sync_key_100" not in restored


def test_digest_arena_merge():
    arena1 = GossipDigestArena(capacity=200, error_rate=0.01)
    arena1.add("item_a")

    arena2 = GossipDigestArena(capacity=200, error_rate=0.01)
    arena2.add("item_b")

    arena1.merge_arena(arena2)

    assert "item_a" in arena1
    assert "item_b" in arena1


def test_digest_arena_concurrency():
    arena = GossipDigestArena(capacity=2000, error_rate=0.01)

    def worker(prefix: str, count: int):
        for i in range(count):
            arena.add(f"{prefix}_{i}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(worker, "worker1", 100),
            executor.submit(worker, "worker2", 100),
            executor.submit(lambda: [arena.contains(f"worker1_{i}") for i in range(50)], None),
        ]
        concurrent.futures.wait(futures)

    assert "worker1_50" in arena
    assert "worker2_50" in arena
