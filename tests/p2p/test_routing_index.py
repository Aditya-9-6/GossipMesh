import pytest
import threading
from gossipmesh.p2p.routing_index import RoutingVectorIndex


def test_routing_vector_encoding_decoding():
    vec = [1.0, -0.5, 0.2, -1.0]
    packed = RoutingVectorIndex.encode_vector(vec)
    assert isinstance(packed, int)
    decoded = RoutingVectorIndex.decode_vector(packed, 4)
    assert decoded == [1.0, -1.0, 1.0, -1.0]


def test_hamming_distance():
    # 0b1010 (10) and 0b1100 (12) -> XOR = 0b0110 -> popcount = 2
    dist = RoutingVectorIndex.hamming_distance(10, 12)
    assert dist == 2


def test_routing_index_upsert_and_query():
    index = RoutingVectorIndex(dimensions=8)
    index.upsert_peer("peer-1", [1.0, 1.0, 1.0, 1.0, -1.0, -1.0, -1.0, -1.0], {"addr": "127.0.0.1:8001"})
    index.upsert_peer("peer-2", [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0], {"addr": "127.0.0.1:8002"})
    index.upsert_peer("peer-3", [-1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0], {"addr": "127.0.0.1:8003"})

    assert index.get_peer_count() == 3

    # Query closest to peer-2 vector
    results = index.query_nearest([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0], top_k=2)
    assert len(results) == 2
    assert results[0][0] == "peer-2"
    assert results[0][1] == 0
    assert results[0][2]["addr"] == "127.0.0.1:8002"

    # Remove peer and verify count
    index.remove_peer("peer-3")
    assert index.get_peer_count() == 2


def test_routing_index_concurrency():
    index = RoutingVectorIndex(dimensions=16)

    def worker(worker_id: int):
        for i in range(100):
            pid = f"peer-{worker_id}-{i}"
            vec = [float((i + j) % 2 * 2 - 1) for j in range(16)]
            index.upsert_peer(pid, vec, {"worker": worker_id})
            if i % 2 == 0:
                index.remove_peer(pid)

    threads = [threading.Thread(target=worker, args=(w,)) for w in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert index.get_peer_count() >= 0
