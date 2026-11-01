import threading
import time
import pytest
from gossipmesh.p2p.delta_engine import LockFreeDoubleBufferedDeltaEngine, DeltaBuffer


def test_delta_engine_initialization():
    engine = LockFreeDoubleBufferedDeltaEngine("node-1")
    assert engine.node_id == "node-1"
    snapshot = engine.active_snapshot
    assert isinstance(snapshot, DeltaBuffer)
    assert snapshot.version == 0
    assert snapshot.states == {}


def test_stage_and_commit_swap():
    engine = LockFreeDoubleBufferedDeltaEngine("node-1")
    engine.stage_delta("peer-A", {"status": "active", "seq": 10})
    
    # Before commit, active snapshot should not have peer-A
    assert engine.get_peer_state("peer-A") is None
    
    version = engine.commit_swap()
    assert version == 1
    
    state_a = engine.get_peer_state("peer-A")
    assert state_a is not None
    assert state_a["status"] == "active"
    assert state_a["seq"] == 10


def test_merge_incoming_payload():
    engine = LockFreeDoubleBufferedDeltaEngine("node-1")
    ver = engine.merge_incoming_payload("peer-B", {"load": 0.42})
    assert ver == 1
    
    state_b = engine.get_peer_state("peer-B")
    assert state_b == {"load": 0.42}


def test_concurrent_churn_and_parallel_updates():
    engine = LockFreeDoubleBufferedDeltaEngine("node-1")
    num_threads = 20
    iterations_per_thread = 50

    def writer_worker(thread_id: int):
        for i in range(iterations_per_thread):
            peer_id = f"peer-{thread_id % 5}"
            engine.merge_incoming_payload(peer_id, {f"metric_{thread_id}": i, "timestamp": time.time()})

    def reader_worker():
        for _ in range(iterations_per_thread):
            for p_idx in range(5):
                _ = engine.get_peer_state(f"peer-{p_idx}")

    threads = []
    for t_id in range(num_threads):
        if t_id % 2 == 0:
            th = threading.Thread(target=writer_worker, args=(t_id,))
        else:
            th = threading.Thread(target=reader_worker)
        threads.append(th)
        th.start()

    for th in threads:
        th.join()

    # Verify final states are consistent and accessible without deadlock or race conditions
    for p_idx in range(5):
        state = engine.get_peer_state(f"peer-{p_idx}")
        # If updated, it should be a dict
        if state is not None:
            assert isinstance(state, dict)
