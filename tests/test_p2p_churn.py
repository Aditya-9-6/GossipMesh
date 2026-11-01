import time
import pytest
from gossipmesh.p2p.churn import ChurnDefenseConfig, PeerChurnTracker, MeshChurnManager
from gossipmesh.p2p.node import PeerManager


def test_peer_churn_tracker_normal_variance():
    config = ChurnDefenseConfig(window_size=10, entropy_variance_threshold=0.01, max_allowed_ticks_variance_exceeded=3)
    tracker = PeerChurnTracker("peer-normal", config)

    # Feed varying metadata vectors resulting in fluctuating entropy
    vectors = [
        {"a": 10, "b": 20},
        {"a": 15, "b": 5},
        {"a": 2, "b": 30},
        {"a": 25, "b": 12},
        {"a": 5, "b": 5},
        {"a": 18, "b": 22},
    ]

    for vec in vectors:
        tracker.record_heartbeat_metadata(vec)

    is_sybil, variance = tracker.evaluate_churn_defense()
    assert not is_sybil
    assert variance >= config.entropy_variance_threshold
    assert not tracker.is_quarantined()


def test_peer_churn_tracker_sybil_flood_quarantine():
    config = ChurnDefenseConfig(window_size=10, entropy_variance_threshold=0.05, max_allowed_ticks_variance_exceeded=2)
    tracker = PeerChurnTracker("peer-sybil", config)

    # Feed static identical vectors resulting in zero entropy variance (Sybil flooding fake heartbeats)
    static_vector = {"node_seq": 100}
    
    for _ in range(10):
        tracker.record_heartbeat_metadata(static_vector)

    # First evaluation (tick 1)
    is_sybil_1, _ = tracker.evaluate_churn_defense()
    # Second evaluation (tick 2 - crosses threshold of max_allowed_ticks_variance_exceeded=2)
    is_sybil_2, _ = tracker.evaluate_churn_defense()

    assert is_sybil_2 is True
    assert tracker.is_quarantined() is True


def test_mesh_churn_manager_integration():
    manager = MeshChurnManager(ChurnDefenseConfig(window_size=5, entropy_variance_threshold=0.01, max_allowed_ticks_variance_exceeded=1))
    
    # Feed fluctuating vector
    manager.process_heartbeat("peer-1", {"x": 10, "y": 20})
    manager.process_heartbeat("peer-1", {"x": 15, "y": 5})
    manager.process_heartbeat("peer-1", {"x": 2, "y": 30})
    manager.process_heartbeat("peer-1", {"x": 25, "y": 12})
    manager.process_heartbeat("peer-1", {"x": 8, "y": 18})
    
    is_sybil, _ = manager.process_heartbeat("peer-1", {"x": 10, "y": 20})
    assert not manager.is_peer_quarantined("peer-1")

    # Feed identical flooding vectors
    for _ in range(10):
        is_sybil, _ = manager.process_heartbeat("peer-2", {"flat": 42})

    assert manager.is_peer_quarantined("peer-2") is True


def test_peer_manager_churn_integration():
    peer_mgr = PeerManager(churn_config=ChurnDefenseConfig(window_size=5, entropy_variance_threshold=0.01, max_allowed_ticks_variance_exceeded=1))
    peer_mgr.add_peer("node-sybil", "127.0.0.1:8001")

    for _ in range(10):
        peer_mgr.record_peer_heartbeat("node-sybil", {"static": 99})

    active_peers = peer_mgr.get_active_peers()
    assert "node-sybil" not in active_peers

    statuses = peer_mgr.get_all_peer_statuses()
    assert statuses["node-sybil"]["sybil_quarantined"] is True
