"""
Sliding-Window Adaptive Congestion Control for Gossip Streams.

Dynamically regulates packet transmission rates based on real-time ACK feedback,
round-trip time (RTT), and network jitter without external dependencies.
Maintains strict O(1) event complexity and decouples congestion states from
underlying socket descriptors.
"""

import enum
import math
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


class CongestionState(str, enum.Enum):
    """Congestion control operating phases."""

    SLOW_START = "slow_start"
    CONGESTION_AVOIDANCE = "congestion_avoidance"
    FAST_RECOVERY = "fast_recovery"


@dataclass(frozen=True)
class CongestionConfig:
    """Configuration parameters for adaptive sliding window control."""

    initial_cwnd: float = 2.0
    min_cwnd: float = 1.0
    max_cwnd: float = 128.0
    initial_ssthresh: float = 32.0
    rtt_alpha: float = 0.125
    jitter_beta: float = 0.25
    min_pacing_delay: float = 0.0005
    max_pacing_delay: float = 1.0
    loss_reduction_factor: float = 0.5


@dataclass
class InFlightPacket:
    """Metadata for an unacknowledged packet in flight."""

    packet_id: str
    sent_at: float
    size_bytes: int


class NetworkJitterEstimator:
    """Estimates statistical network jitter via Jacobson / RFC 3550 EWMA."""

    def __init__(self, beta: float = 0.25) -> None:
        self.beta = beta
        self.jitter: float = 0.0
        self._prev_rtt: Optional[float] = None

    def update(self, sample_rtt: float) -> float:
        """Updates jitter metric with a new sample RTT in O(1) time."""
        if sample_rtt < 0.0:
            raise ValueError("sample_rtt cannot be negative")

        if self._prev_rtt is None:
            self._prev_rtt = sample_rtt
            self.jitter = 0.0
        else:
            transit_diff = abs(sample_rtt - self._prev_rtt)
            self.jitter = (1.0 - self.beta) * self.jitter + self.beta * transit_diff
            self._prev_rtt = sample_rtt

        return self.jitter

    def get_jitter(self) -> float:
        """Returns the current estimated jitter in seconds."""
        return self.jitter

    def reset(self) -> None:
        """Resets the jitter estimator state."""
        self.jitter = 0.0
        self._prev_rtt = None


class SlidingWindowCongestionController:
    """
    Sliding-window congestion controller with dynamic pacing and ACK feedback.
    Thread-safe and operates in strict O(1) per packet event.
    """

    def __init__(self, config: Optional[CongestionConfig] = None) -> None:
        self.config = config or CongestionConfig()
        self.cwnd: float = float(self.config.initial_cwnd)
        self.ssthresh: float = float(self.config.initial_ssthresh)
        self.state: CongestionState = CongestionState.SLOW_START
        self.srtt: Optional[float] = None
        self.jitter_estimator = NetworkJitterEstimator(beta=self.config.jitter_beta)
        self._in_flight: Dict[str, InFlightPacket] = {}
        self._loss_count: int = 0
        self._lock = threading.Lock()

    def can_send(self) -> bool:
        """Checks if transmission window permits sending another packet."""
        with self._lock:
            return len(self._in_flight) < math.floor(self.cwnd)

    def on_packet_sent(
        self, packet_id: str, size_bytes: int = 1, sent_at: Optional[float] = None
    ) -> bool:
        """
        Registers an outgoing packet in the in-flight sliding window.
        Returns True if sent within window capacity, False otherwise.
        """
        if not packet_id:
            raise ValueError("packet_id cannot be empty")
        if size_bytes <= 0:
            raise ValueError("size_bytes must be positive")

        timestamp = time.monotonic() if sent_at is None else sent_at
        with self._lock:
            if len(self._in_flight) >= math.floor(self.cwnd):
                return False
            self._in_flight[packet_id] = InFlightPacket(
                packet_id=packet_id, sent_at=timestamp, size_bytes=size_bytes
            )
            return True

    def on_ack_received(
        self, packet_id: str, ack_at: Optional[float] = None
    ) -> Optional[float]:
        """
        Processes an incoming packet ACK, updates RTT, jitter, and expands cwnd.
        Returns the measured sample RTT, or None if packet was not tracked.
        """
        arrival_time = time.monotonic() if ack_at is None else ack_at
        with self._lock:
            packet = self._in_flight.pop(packet_id, None)
            if packet is None:
                return None

            sample_rtt = max(0.0, arrival_time - packet.sent_at)
            self._update_rtt_and_jitter(sample_rtt)
            self._advance_window()
            return sample_rtt

    def on_loss_detected(self, packet_id: Optional[str] = None) -> None:
        """
        Applies multiplicative decrease and transitions state upon packet loss.
        """
        with self._lock:
            self._loss_count += 1
            if packet_id:
                self._in_flight.pop(packet_id, None)

            # Halve window down to minimum bound
            new_ssthresh = max(
                self.config.min_cwnd, self.cwnd * self.config.loss_reduction_factor
            )
            self.ssthresh = new_ssthresh
            self.cwnd = max(self.config.min_cwnd, new_ssthresh)
            self.state = CongestionState.FAST_RECOVERY

    def get_pacing_delay(self) -> float:
        """
        Computes the target transmission pacing delay between outgoing packets.
        """
        with self._lock:
            effective_rtt = self.srtt if self.srtt is not None else 0.05
            jitter = self.jitter_estimator.get_jitter()
            delay = (effective_rtt + 2.0 * jitter) / max(1.0, self.cwnd)
            return max(
                self.config.min_pacing_delay, min(self.config.max_pacing_delay, delay)
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Returns snapshot telemetry of the congestion control instance."""
        with self._lock:
            return {
                "cwnd": round(self.cwnd, 4),
                "ssthresh": round(self.ssthresh, 4),
                "in_flight_count": len(self._in_flight),
                "state": self.state.value,
                "srtt": round(self.srtt, 6) if self.srtt is not None else None,
                "jitter": round(self.jitter_estimator.get_jitter(), 6),
                "loss_events": self._loss_count,
            }

    def reset(self) -> None:
        """Resets all window, state, and telemetry metrics."""
        with self._lock:
            self.cwnd = float(self.config.initial_cwnd)
            self.ssthresh = float(self.config.initial_ssthresh)
            self.state = CongestionState.SLOW_START
            self.srtt = None
            self.jitter_estimator.reset()
            self._in_flight.clear()
            self._loss_count = 0

    def _update_rtt_and_jitter(self, sample_rtt: float) -> None:
        """Internal helper to calculate EWMA SRTT and Jitter."""
        self.jitter_estimator.update(sample_rtt)
        if self.srtt is None:
            self.srtt = sample_rtt
        else:
            alpha = self.config.rtt_alpha
            self.srtt = (1.0 - alpha) * self.srtt + alpha * sample_rtt

    def _advance_window(self) -> None:
        """Internal helper to expand congestion window according to TCP rules."""
        if self.state == CongestionState.SLOW_START:
            self.cwnd += 1.0
            if self.cwnd >= self.ssthresh:
                self.state = CongestionState.CONGESTION_AVOIDANCE
        elif self.state == CongestionState.CONGESTION_AVOIDANCE:
            self.cwnd += 1.0 / max(1.0, self.cwnd)
        elif self.state == CongestionState.FAST_RECOVERY:
            self.state = CongestionState.CONGESTION_AVOIDANCE

        self.cwnd = min(self.config.max_cwnd, max(self.config.min_cwnd, self.cwnd))


class StreamCongestionManager:
    """Manages independent sliding-window controllers per peer connection."""

    def __init__(self, default_config: Optional[CongestionConfig] = None) -> None:
        self.default_config = default_config or CongestionConfig()
        self._controllers: Dict[str, SlidingWindowCongestionController] = {}
        self._lock = threading.Lock()

    def get_controller(self, peer_id: str) -> SlidingWindowCongestionController:
        """Returns or creates a congestion controller for the specified peer."""
        if not peer_id:
            raise ValueError("peer_id cannot be empty")
        with self._lock:
            if peer_id not in self._controllers:
                self._controllers[peer_id] = SlidingWindowCongestionController(
                    config=self.default_config
                )
            return self._controllers[peer_id]

    def remove_peer(self, peer_id: str) -> None:
        """Removes tracking state for a disconnected peer."""
        with self._lock:
            self._controllers.pop(peer_id, None)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Returns telemetry metrics across all active peer streams."""
        with self._lock:
            return {
                peer_id: ctrl.get_metrics()
                for peer_id, ctrl in self._controllers.items()
            }
