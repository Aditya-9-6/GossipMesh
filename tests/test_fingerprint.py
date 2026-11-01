import pytest
import concurrent.futures
from gossipmesh.p2p.fingerprint import BitsetFingerprint

def test_fingerprint_basic_operations():
    bf = BitsetFingerprint(capacity=1000, fp_rate=0.01)
    
    assert not bf.contains("node_alpha")
    assert not bf.contains(b"node_beta")
    
    bf.add("node_alpha")
    bf.add(b"node_beta")
    
    assert bf.contains("node_alpha")
    assert bf.contains(b"node_beta")
    assert not bf.contains("node_gamma")


def test_fingerprint_serialization():
    bf1 = BitsetFingerprint(capacity=500, fp_rate=0.05)
    bf1.add("peer_1")
    bf1.add("peer_2")
    
    raw_bytes = bf1.to_bytes()
    bf2 = BitsetFingerprint.from_bytes(capacity=500, fp_rate=0.05, buffer=raw_bytes)
    
    assert bf2.contains("peer_1")
    assert bf2.contains("peer_2")
    assert not bf2.contains("peer_3")


def test_fingerprint_union():
    bf1 = BitsetFingerprint(capacity=500, fp_rate=0.01)
    bf2 = BitsetFingerprint(capacity=500, fp_rate=0.01)
    
    bf1.add("peer_a")
    bf2.add(
        "peer_b"
    )
    
    bf1.union_inplace(bf2)
    
    assert bf1.contains("peer_a")
    assert bf1.contains("peer_b")


def test_concurrency_stress():
    bf = BitsetFingerprint(capacity=10000, fp_rate=0.001)
    
    def worker(start_idx: int):
        for i in range(100):
            bf.add(f"node_{start_idx + i}")
            
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i * 100) for i in range(8)]
        concurrent.futures.wait(futures)
        
    for i in range(800):
        assert bf.contains(f"node_{i}")
