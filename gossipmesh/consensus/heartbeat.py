"""
Heartbeat manager with decentralized adaptive backoff for partition avoidance and rapid mesh healing.
"""

from __future__ import annotations

import time
import threading
import logging
from typing import Dict, List, Optional, Tuple

from gossipmesh.consensus.backoff import AdaptiveBackoffCalculator

logger = logging.getLogger(__name__)


class NodeHeartbeatState:
    """Tracks individual peer heartbeat metrics, latency history, and backoff states."""

    def __init__(self, node_id: str, max_latency_samples: int = 50):
        self.node_id = node_id
        self.consecutive_failures = 0
        self.last_ping_time = 0.0
        self.last_ack_time = 0.0
        self.latencies: List[float] = []
        self.max_latency_samples = max_latency_samples
        self.is_partitioned = False

    def record_success(self, rtt: float) -> None:
        self.consecutive_failures = 0
        self.last_ack_time = time.time()
        self.is_partitioned = False
        self.latencies.append(rtt)
        if len(self.latencies) > self.max_latency_samples:
            self.latencies.pop(0)

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.last_ack_time = time.time()

    @property
    def rolling_avg_latency(self) -> float:
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)


class AdaptiveHeartbeatManager:
    """
    Manages adaptive heartbeat cycles across peers in the gossip mesh with thread safety.
    """

    def __init__(
        self,
        calculator: Optional[AdaptiveBackoffCalculator] = None,
        partition_failure_threshold: int = 3,
    ):
        self.calculator = calculator or AdaptiveBackoffCalculator()
        self.partition_failure_threshold = partition_failure_threshold
        self.states: Dict[str, NodeHeartbeatState] = {}
        self._lock = threading.Lock()

    def get_or_create_state(self, node_id: str) -> NodeHeartbeatState:
        with self._lock:
            if node_id not in self.states:
                self.states[node_id] = NodeHeartbeatState(node_id)
            return self.states[node_id]

    def record_ping_sent(self, node_id: str) -> float:
        state = self.get_or_create_state(node_id)
        with self._lock:
            state.last_ping_time = time.time()
            return self.get_next_interval(node_id)

    def record_ack_received(self, node_id: str, rtt: float) -> None:
        state = self.get_or_create_state(node_id)
        with self._lock:
            state.record_success(rtt)

    def record_timeout(self, node_id: str) -> None:
        state = self.get_or_create_state(node_id)
        with self._lock:
            state.record_failure()
            if state.consecutive_failures >= self.partition_failure_threshold:
                state.is_partitioned = True
                logger.warning(f"Node {node_id} marked partitioned after {state.consecutive_failures} failures.")

    def get_next_interval(self, node_id: str) -> float:
        state = self.get_or_create_state(node_id)
        with self._lock:
            return self.calculator.compute_backoff(
                consecutive_failures=state.consecutive_failures,
                rolling_avg_latency=state.rolling_avg_latency,
                partition_detected=state.is_partitioned,
            )

    def check_mesh_healing(self, node_id: str) -> bool:
        """Resets partition state if rapid recovery ACK received (sub-second convergence)."""
        state = self.get_or_create_state(node_id)
        with self._lock:
            if state.is_partitioned:
                state.is_partitioned = False
                state.consecutive_failures = 0
                logger.info(f"Mesh healing detected for node {node_id}. Resetting backoff interval.")
                return True
            return False
