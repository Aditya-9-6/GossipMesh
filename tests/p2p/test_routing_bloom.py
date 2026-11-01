import pytest
import threading
from gossipmesh.p2p.routing_bloom import BloomFilterLayer, ScalableBloomRoutingTable


def test_bloom_layer_basic():
    layer = BloomFilterLayer(capacity=100, error_rate=0.01)
    assert "node_1" not in layer
    layer.add("node_1")
    assert "node_1" in layer
    assert "node_2" not in layer


def test_scalable_bloom_routing_table_resizing():
    table = ScalableBloomRoutingTable(initial_capacity=10, error_rate=0.01, scaling_factor=2)
    for i in range(50):
        table.add(f"node_{i}")

    # Verify all inserted nodes are found (zero false negatives)
    for i in range(50):
        assert f"node_{i}" in table

    assert table.layer_count > 1
    assert table.total_nodes == 50


def test_concurrency_and_thread_safety():
    table = ScalableBloomRoutingTable(initial_capacity=500, error_rate=0.001)
    num_threads = 8
    nodes_per_thread = 200

    def worker(thread_id: int):
        for i in range(nodes_per_thread):
            node_id = f"t{thread_id}_node_{i}"
            table.add(node_id)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    # Verify reachability across all concurrently added nodes
    for t in range(num_threads):
        for i in range(nodes_per_thread):
            assert f"t{t}_node_{i}" in table
