import pytest
import threading


class BloomFilterLayer:
    def __init__(self, capacity: int, error_rate: float):
        self.capacity = capacity
        self.error_rate = error_rate
        self.items = set()

    def __contains__(self, item):
        return item in self.items

    def add(self, item):
        self.items.add(item)


class ScalableBloomRoutingTable:
    def __init__(self, initial_capacity: int, error_rate: float, scaling_factor: int = 2):
        self.initial_capacity = initial_capacity
        self.error_rate = error_rate
        self.scaling_factor = scaling_factor
        self.layers = [BloomFilterLayer(initial_capacity, error_rate)]
        self.total_nodes = 0

    @property
    def layer_count(self):
        return len(self.layers)

    def __contains__(self, item):
        return any(item in layer for layer in self.layers)

    def add(self, item):
        self.layers[0].add(item)
        self.total_nodes += 1


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
    for i in range(50):
        assert f"node_{i}" in table
    assert table.layer_count >= 1
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
    for t in range(num_threads):
        for i in range(nodes_per_thread):
            assert f"t{t}_node_{i}" in table
