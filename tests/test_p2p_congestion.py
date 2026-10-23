"""
Unit tests for GossipMesh P2P Sliding-Window Adaptive Congestion Control.
"""

import threading
import time
import pytest
from gossipmesh.p2p.congestion import (
    CongestionConfig,
    CongestionState,
    NetworkJitterEstimator,
    SlidingWindowCongestionController,
    StreamCongestionManager,
)


class TestNetworkJitterEstimator:
    def test_initial_update_and_properties(self):
        estimator = NetworkJitterEstimator(beta=0.25)
        assert estimator.get_jitter() == 0.0

        j1 = estimator.update(0.050)
        assert j1 == 0.0
        assert estimator.get_jitter() == 0.0

        # Transit diff = |0.070 - 0.050| = 0.020 -> jitter = 0.75 * 0 + 0.25 * 0.020 = 0.005
        j2 = estimator.update(0.070)
        assert pytest.approx(j2, rel=1e-3) == 0.005
        assert pytest.approx(estimator.get_jitter(), rel=1e-3) == 0.005

    def test_negative_rtt_raises_error(self):
        estimator = NetworkJitterEstimator()
        with pytest.raises(ValueError, match="negative"):
            estimator.update(-0.01)

    def test_estimator_reset(self):
        estimator = NetworkJitterEstimator()
        estimator.update(0.020)
        estimator.update(0.060)
        assert estimator.get_jitter() > 0.0

        estimator.reset()
        assert estimator.get_jitter() == 0.0
        assert estimator._prev_rtt is None


class TestSlidingWindowCongestionController:
    def test_initial_state_and_can_send(self):
        config = CongestionConfig(initial_cwnd=3.0, min_cwnd=1.0, max_cwnd=16.0)
        ctrl = SlidingWindowCongestionController(config=config)

        assert ctrl.state == CongestionState.SLOW_START
        assert ctrl.cwnd == 3.0
        assert ctrl.can_send() is True

    def test_window_saturation(self):
        config = CongestionConfig(initial_cwnd=2.0)
        ctrl = SlidingWindowCongestionController(config=config)

        assert ctrl.on_packet_sent("p1") is True
        assert ctrl.can_send() is True

        assert ctrl.on_packet_sent("p2") is True
        # Window is now saturated (2 in flight >= floor(cwnd=2.0))
        assert ctrl.can_send() is False
        assert ctrl.on_packet_sent("p3") is False

    def test_invalid_packet_inputs(self):
        ctrl = SlidingWindowCongestionController()
        with pytest.raises(ValueError, match="empty"):
            ctrl.on_packet_sent("")
        with pytest.raises(ValueError, match="positive"):
            ctrl.on_packet_sent("p1", size_bytes=0)
        with pytest.raises(ValueError, match="positive"):
            ctrl.on_packet_sent("p1", size_bytes=-5)

    def test_slow_start_growth(self):
        config = CongestionConfig(initial_cwnd=2.0, initial_ssthresh=6.0)
        ctrl = SlidingWindowCongestionController(config=config)

        t0 = time.monotonic()
        ctrl.on_packet_sent("p1", sent_at=t0)
        rtt = ctrl.on_ack_received("p1", ack_at=t0 + 0.025)

        assert pytest.approx(rtt, rel=1e-3) == 0.025
        # In Slow Start, cwnd increases by 1 per ACK
        assert ctrl.cwnd == 3.0
        assert ctrl.state == CongestionState.SLOW_START

    def test_transition_to_congestion_avoidance(self):
        config = CongestionConfig(initial_cwnd=3.0, initial_ssthresh=4.0)
        ctrl = SlidingWindowCongestionController(config=config)

        t0 = time.monotonic()
        ctrl.on_packet_sent("p1", sent_at=t0)
        ctrl.on_ack_received("p1", ack_at=t0 + 0.010)

        # cwnd reached ssthresh (4.0) -> transitions to Congestion Avoidance
        assert ctrl.cwnd == 4.0
        assert ctrl.state == CongestionState.CONGESTION_AVOIDANCE

        # In Congestion Avoidance, cwnd increases by 1 / cwnd
        ctrl.on_packet_sent("p2", sent_at=t0)
        ctrl.on_ack_received("p2", ack_at=t0 + 0.015)
        expected_cwnd = 4.0 + (1.0 / 4.0)
        assert pytest.approx(ctrl.cwnd, rel=1e-3) == expected_cwnd

    def test_untracked_ack_returns_none(self):
        ctrl = SlidingWindowCongestionController()
        rtt = ctrl.on_ack_received("unknown_packet_id")
        assert rtt is None

    def test_loss_detection_and_multiplicative_decrease(self):
        config = CongestionConfig(initial_cwnd=10.0, loss_reduction_factor=0.5, min_cwnd=1.0)
        ctrl = SlidingWindowCongestionController(config=config)
        ctrl.on_packet_sent("p1")

        ctrl.on_loss_detected(packet_id="p1")

        assert ctrl.state == CongestionState.FAST_RECOVERY
        assert ctrl.ssthresh == 5.0
        assert ctrl.cwnd == 5.0
        assert ctrl.can_send() is True

        # Subsequent ACK exits fast recovery back to congestion avoidance
        t0 = time.monotonic()
        ctrl.on_packet_sent("p2", sent_at=t0)
        ctrl.on_ack_received("p2", ack_at=t0 + 0.020)
        assert ctrl.state == CongestionState.CONGESTION_AVOIDANCE

    def test_pacing_delay_calculation(self):
        config = CongestionConfig(initial_cwnd=4.0, min_pacing_delay=0.001, max_pacing_delay=0.5)
        ctrl = SlidingWindowCongestionController(config=config)

        # Before any ACK, uses default RTT
        pacing1 = ctrl.get_pacing_delay()
        assert config.min_pacing_delay <= pacing1 <= config.max_pacing_delay

        # After ACK with known RTT
        t0 = time.monotonic()
        ctrl.on_packet_sent("p1", sent_at=t0)
        ctrl.on_ack_received("p1", ack_at=t0 + 0.040)
        pacing2 = ctrl.get_pacing_delay()
        assert config.min_pacing_delay <= pacing2 <= config.max_pacing_delay

    def test_metrics_telemetry(self):
        ctrl = SlidingWindowCongestionController()
        ctrl.on_packet_sent("p1")
        metrics = ctrl.get_metrics()

        assert "cwnd" in metrics
        assert "ssthresh" in metrics
        assert metrics["in_flight_count"] == 1
        assert metrics["state"] == "slow_start"
        assert metrics["loss_events"] == 0

    def test_controller_reset(self):
        ctrl = SlidingWindowCongestionController()
        ctrl.on_packet_sent("p1")
        ctrl.on_loss_detected("p1")
        assert ctrl.get_metrics()["loss_events"] == 1

        ctrl.reset()
        m = ctrl.get_metrics()
        assert m["cwnd"] == ctrl.config.initial_cwnd
        assert m["state"] == "slow_start"
        assert m["in_flight_count"] == 0
        assert m["loss_events"] == 0


class TestStreamCongestionManager:
    def test_peer_isolation_and_management(self):
        mgr = StreamCongestionManager()
        c_a = mgr.get_controller("peer_alpha")
        c_b = mgr.get_controller("peer_beta")

        assert c_a is not c_b
        assert mgr.get_controller("peer_alpha") is c_a

        c_a.on_packet_sent("pa_1")
        assert c_a.get_metrics()["in_flight_count"] == 1
        assert c_b.get_metrics()["in_flight_count"] == 0

        all_m = mgr.get_all_metrics()
        assert "peer_alpha" in all_m
        assert "peer_beta" in all_m

        mgr.remove_peer("peer_alpha")
        assert "peer_alpha" not in mgr.get_all_metrics()

    def test_empty_peer_id_error(self):
        mgr = StreamCongestionManager()
        with pytest.raises(ValueError, match="empty"):
            mgr.get_controller("")


class TestConcurrencySafety:
    def test_concurrent_sends_and_acks(self):
        config = CongestionConfig(initial_cwnd=64.0, max_cwnd=128.0)
        ctrl = SlidingWindowCongestionController(config=config)
        errors = []

        def worker(worker_id: int):
            try:
                for i in range(25):
                    pkt_id = f"w{worker_id}_p{i}"
                    now = time.monotonic()
                    sent = ctrl.on_packet_sent(pkt_id, sent_at=now)
                    if sent:
                        time.sleep(0.001)
                        ctrl.on_ack_received(pkt_id, ack_at=now + 0.005)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert ctrl.get_metrics()["in_flight_count"] == 0
        assert ctrl.cwnd > config.initial_cwnd
