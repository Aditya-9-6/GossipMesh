from __future__ import annotations

import concurrent.futures
import pytest
from gossipmesh.routing.skiplist import SkipList


def test_skiplist_insert_and_search() -> None:
    sl = SkipList(capacity=100, max_level=8)
    sl.insert("node_a", value="ip_a:8080", score=0.9, latency=12.5)
    sl.insert("node_b", value="ip_b:8080", score=0.5, latency=45.0)

    assert sl.search("node_a") == (0.9, 12.5, "ip_a:8080")
    assert sl.search("node_b") == (0.5, 45.0, "ip_b:8080")
    assert sl.search("node_c") is None


def test_skiplist_update() -> None:
    sl = SkipList()
    sl.insert("node_a", value="v1", score=1.0, latency=10.0)
    sl.insert("node_a", value="v2", score=2.0, latency=5.0)
    assert sl.search("node_a") == (2.0, 5.0, "v2")
    assert sl.size == 1


def test_skiplist_delete() -> None:
    sl = SkipList()
    sl.insert("node_a", value="v1")
    sl.insert("node_b", value="v2")
    assert sl.size == 2

    assert sl.delete("node_a") is True
    assert sl.search("node_a") is None
    assert sl.size == 1
    assert sl.delete("nonexistent") is False


def test_skiplist_range_query() -> None:
    sl = SkipList()
    sl.insert("node_1", value="val1")
    sl.insert("node_3", value="val3")
    sl.insert("node_2", value="val2")
    sl.insert("node_5", value="val5")

    results = sl.range_query("node_1", "node_3")
    keys = [k for k, v in results]
    assert keys == ["node_1", "node_2", "node_3"]


def test_skiplist_concurrent_access() -> None:
    sl = SkipList(capacity=1000, max_level=16)

    def worker(start: int, end: int) -> None:
        for i in range(start, end):
            key = f"node_{i:04d}"
            sl.insert(key, value=i, score=float(i), latency=float(i))

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(worker, 0, 250),
            executor.submit(worker, 250, 500),
            executor.submit(worker, 500, 750),
            executor.submit(worker, 750, 1000),
        ]
        concurrent.futures.wait(futures)

    assert sl.size == 1000
    assert sl.search("node_0500") == (500.0, 500.0, 500)


def test_skiplist_capacity_eviction() -> None:
    sl = SkipList(capacity=5, max_level=4)
    for i in range(10):
        sl.insert(f"node_{i}", value=i)
    assert sl.size <= 5
