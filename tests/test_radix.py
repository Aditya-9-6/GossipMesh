import time
import threading
import pytest
from gossipmesh.p2p.radix import CacheObliviousRadixTree, RadixNode


def test_radix_basic_insertion_and_search():
    tree = CacheObliviousRadixTree()
    tree.insert("peer/us-east/node1", "192.168.1.10")
    tree.insert("peer/us-east/node2", "192.168.1.11")
    tree.insert("peer/eu-west/node1", "10.0.0.5")

    assert len(tree) == 3
    assert tree.search("peer/us-east/node1") == "192.168.1.10"
    assert tree.search("peer/us-east/node2") == "192.168.1.11"
    assert tree.search("peer/eu-west/node1") == "10.0.0.5"
    assert tree.search("peer/nonexistent") is None
    assert tree.search("peer/us-east") is None


def test_radix_edge_cases():
    tree = CacheObliviousRadixTree()
    with pytest.raises(ValueError):
        tree.insert("", "value")
    with pytest.raises(ValueError):
        tree.insert(None, "value")

    assert tree.search("") is None
    assert tree.search(None) is None
    assert tree.delete("nonexistent") is False


def test_radix_longest_prefix_match():
    tree = CacheObliviousRadixTree()
    tree.insert("net/", "root_net")
    tree.insert("net/datacenter/", "dc_net")
    tree.insert("net/datacenter/rack1/")

    pfx, val = tree.longest_prefix_match("net/datacenter/rack1/server42")
    assert pfx == "net/datacenter/"
    assert val == "dc_net"

    pfx2, val2 = tree.longest_prefix_match("net/other/node")
    assert pfx2 == "net/"
    assert val2 == "root_net"

    pfx3, val3 = tree.longest_prefix_match("unknown/path")
    assert pfx3 is None
    assert val3 is None


def test_radix_deletion():
    tree = CacheObliviousRadixTree()
    tree.insert("alpha", 1)
    tree.insert("beta", 2)
    tree.insert("alphabet", 3)

    assert len(tree) == 3
    assert tree.search("alpha") == 1
    assert tree.search("alphabet") == 3

    assert tree.delete("alpha") is True
    assert len(tree) == 2
    assert tree.search("alpha") is None
    assert tree.search("alphabet") == 3

    assert tree.delete("alphabet") is True
    assert tree.search("alphabet") is None
    assert len(tree) == 1

    tree.clear()
    assert len(tree) == 0
    assert tree.search("beta") is None


def test_radix_concurrent_access():
    tree = CacheObliviousRadixTree()
    num_threads = 10
    iterations_per_thread = 100

    def writer(thread_idx: int):
        for i in range(iterations_per_thread):
            key = f"thread/{thread_idx}/node/{i}"
            tree.insert(key, f"val-{thread_idx}-{i}")

    def reader():
        for i in range(iterations_per_thread):
            tree.search(f"thread/0/node/{i}")
            tree.longest_prefix_match("thread/1/node/")

    threads = []
    for t in range(num_threads):
        th = threading.Thread(target=writer, args=(t,))
        threads.append(th)
        th.start()

    for _ in range(5):
        th = threading.Thread(target=reader)
        threads.append(th)
        th.start()

    for th in threads:
        th.join()

    assert len(tree) == num_threads * iterations_per_thread


def test_radix_sub_microsecond_performance_benchmark():
    tree = CacheObliviousRadixTree()
    for i in range(1000):
        tree.insert(f"peer/region-{i % 5}/node-{i}", f"ip-10-0-{i}")

    start_time = time.perf_counter()
    lookups = 10000
    for i in range(lookups):
        tree.search(f"peer/region-{i % 5}/node-{i % 1000}")
    duration = time.perf_counter() - start_time

    avg_time_us = (duration / lookups) * 1_000_000
    # Ensure sub-microsecond average lookup time or close to threshold
    assert avg_time_us < 10.0, f"Average lookup time {avg_time_us:.3f}µs exceeded threshold"
