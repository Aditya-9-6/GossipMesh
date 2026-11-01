from __future__ import annotations

import os
import pytest
import threading
from gossipmesh.routing.kademlia import KademliaNode, KBucket, KademliaRoutingTable


def test_kademlia_node_xor_distance():
    id1 = b"\x00" * 31 + b"\x01"
    id2 = b"\x00" * 31 + b"\x03"
    node1 = KademliaNode(id1, "127.0.0.1:8001")
    
    dist = node1.xor_distance(id2)
    assert dist == 2


def test_k_bucket_operations():
    bucket = KBucket(k=3)
    n1 = KademliaNode(b"\x01" * 32, "127.0.0.1:8001")
    n2 = KademliaNode(b"\x02" * 32, "127.0.0.1:8002")
    n3 = KademliaNode(b"\x03" * 32, "127.0.0.1:8003")
    n4 = KademliaNode(b"\x04" * 32, "127.0.0.1:8004")

    assert bucket.add_node(n1) is None
    assert bucket.add_node(n2) is None
    assert bucket.add_node(n3) is None
    
    # 4th node should go to replacement cache since k=3
    assert bucket.add_node(n4) is None
    assert len(bucket.nodes) == 3
    assert len(bucket.replacement_cache) == 1

    # Remove n1, should promote n4 from replacement cache
    assert bucket.remove_node(n1.node_id) is True
    assert len(bucket.nodes) == 3
    assert n4 in bucket.nodes


def test_kademlia_routing_table_routing_and_split():
    local_id = b"\x00" * 32
    table = KademliaRoutingTable(local_id, k=2)

    n1 = KademliaNode(b"\x80" + b"\x00" * 31, "127.0.0.1:8001")
    n2 = KademliaNode(b"\x40" + b"\x00" * 31, "127.0.0.1:8002")
    n3 = KademliaNode(b"\xC0" + b"\x00" * 31, "127.0.0.1:8003")

    table.add_node(n1)
    table.add_node(n2)
    table.add_node(n3)

    assert table.total_nodes >= 2

    close_nodes = table.find_close_nodes(b"\x80" + b"\x00" * 31, count=2)
    assert len(close_nodes) > 0
    assert close_nodes[0].node_id == n1.node_id


def test_concurrency_safety():
    local_id = b"\xAA" * 32
    table = KademliaRoutingTable(local_id, k=10)

    def worker(prefix_byte: int):
        for i in range(50):
            nid = bytes([prefix_byte]) + bytes([i]) + b"\x00" * 30
            node = KademliaNode(nid, f"127.0.0.1:{9000 + i}")
            table.add_node(node)

    threads = [threading.Thread(target=worker, args=(b,)) for b in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert table.total_nodes > 0
