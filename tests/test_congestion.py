"""
Unit tests for Adaptive Ring-Buffer Congestion Shaper and Sliding-Window Congestion Controller.
"""

import time
import pytest

from gossipmesh.p2p.congestion import (
    CongestionConfig,
    CongestionState,
    NetworkJitterEstimator,
    SlidingWindowCongestionController,
    AdaptiveRingBufferCongestionShaper,
)


def test_network_jitter_estimator():
    estimator = NetworkJitterEstimator(beta=0.25)
    assert estimator.get_jitter() == 0.0

    with pytest.raises(ValueError):
        estimator.update(-0.1)

    j1 = estimator.update(0.100)
    assert j1 == 0.0  # first sample initializes prev_rtt

    j2 = estimator.update(0.150)
    assert j2 > 0.0

    estimator.reset()
    assert estimator.get_jitter() == 0.0


def test_sliding_window_congestion_controller():
    ctrl = SlidingWindowCongestionController()
    assert ctrl.state == CongestionState.SLOW_START
    assert ctrl.can_send() is True

    assert ctrl.register_send("p1", 100) is True
    assert ctrl.register_send("p2", 100) is True

    rtt = ctrl.register_ack("p1")
    assert rtt is not None
    assert rtt >= 0.0

    assert ctrl.register_loss("p2") is True
    assert ctrl.state == CongestionState.FAST_RECOVERY

    metrics = ctrl.get_metrics()
    assert metrics["loss_count"] == 1
    assert "cwnd" in metrics


def test_adaptive_ring_buffer_congestion_shaper_saturation_and_recovery():
    config = CongestionConfig(
        buffer_high_watermark=0.8,
        buffer_low_watermark=0.2,
    )
    shaper = AdaptiveRingBufferCongestionShaper(capacity=10, config=config)
    assert shaper.get_fill_ratio() == 0.0

    # Push items until saturation
    for i in range(10):
        assert shaper.push({"id": f"msg-{i}"}) is True

    assert shaper.get_fill_ratio() == 1.0
    # Further pushes should be dropped
    assert shaper.push({"id": "overflow"}) is False

    metrics = shaper.get_metrics()
    assert metrics["drop_counter"] == 1
    assert metrics["fanout_scaling_factor"] == 0.25

    # Pop items to recover
    for _ in range(8):
        item = shaper.pop()
        assert item is not None

    assert shaper.get_fill_ratio() <= 0.25
    assert shaper.get_metrics()["fanout_scaling_factor"] == 1.0


def test_backpressure_driven_fanout_pruning():
    shaper = AdaptiveRingBufferCongestionShaper(capacity=10)

    # Fill half the buffer to enter intermediate backpressure state
    for i in range(5):
        shaper.push({"id": f"msg-{i}"})

    peer_rankings = {
        "peer_a": 0.95,
        "peer_b": 0.80,
        "peer_c": 0.50,
        "peer_d": 0.20,
    }

    decisions = shaper.prune_low_priority_transmissions(peer_rankings)
    assert len(decisions) == 4
    assert "peer_a" in decisions
    assert "peer_d" in decisions


def test_write_latency_metrics():
    shaper = AdaptiveRingBufferCongestionShaper(capacity=16)
    shaper.record_write_latency(0.012)
    assert shaper.get_write_latency_ewma() > 0.0

    with pytest.raises(ValueError):
        shaper.record_write_latency(-0.005)
