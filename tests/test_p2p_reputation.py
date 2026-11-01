import time
import threading
import pytest
from gossipmesh.p2p.reputation import AdaptivePeerReputationEngine, ReputationConfig


def test_initial_reputation_score():
    engine = AdaptivePeerReputationEngine()
    score = engine.get_score("peer_1")
    assert score == 100.0
    assert not engine.is_quarantined("peer_1")


def test_penalty_and_quarantine():
    config = ReputationConfig(quarantine_threshold=50.0, violation_penalty=60.0)
    engine = AdaptivePeerReputationEngine(config)

    score = engine.record_interaction("peer_bad", latency_ms=100.0, violated=True)
    assert score <= 40.0
    assert engine.is_quarantined("peer_bad")


def test_rewards_and_contributions():
    engine = AdaptivePeerReputationEngine()
    score = engine.record_interaction("peer_good", latency_ms=20.0, payload_valid=True, gossip_contributed=True)
    assert score > 100.0
    metrics = engine.get_metrics("peer_good")
    assert metrics["contribution_count"] == 1
    assert not metrics["is_quarantined"]


def test_concurrency_safety():
    engine = AdaptivePeerReputationEngine()
    peer_id = "peer_concurrent"

    def worker():
        for _ in range(50):
            engine.record_interaction(peer_id, latency_ms=40.0, payload_valid=True, gossip_contributed=True)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    metrics = engine.get_metrics(peer_id)
    assert metrics["reputation_score"] > 100.0
    assert metrics["contribution_count"] == 400
