"""
Adaptive Epidemic TTL Decay via Congestion-Aware Poison-Reverse.

Dynamically lowers message Time-To-Live fields based on local queue depths and
downstream neighbor latency to prevent broadcast storms during partition recovery.
"""

import threading
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class TTLConfig:
    """Configuration parameters for adaptive TTL decay and poison-reverse."""

    base_ttl: int = 16
    min_ttl: int = 1
    queue_congestion_threshold: int = 500
    latency_congestion_threshold_sec: float = 0.05
    decay_penalty: int = 2
    poison_reverse_penalty: int = 4


class AdaptiveTTLManager:
    """
    Manages adaptive TTL reduction and poison-reverse heuristics based on
    local queue depths and downstream peer latencies.
    """

    def __init__(self, config: Optional[TTLConfig] = None) -> None:
        self.config = config or TTLConfig()
        self._peer_latencies: Dict[str, float] = {}
        self._lock = threading.Lock()

    def update_peer_latency(self, peer_id: str, latency_sec: float) -> None:
        """Updates the tracked latency for a specific peer thread-safely."""
        if not peer_id:
            raise ValueError("peer_id cannot be empty")
        if latency_sec < 0.0:
            raise ValueError("latency_sec cannot be negative")
        with self._lock:
            self._peer_latencies[peer_id] = latency_sec

    def get_peer_latency(self, peer_id: str) -> Optional[float]:
        """Retrieves tracked latency for a peer."""
        with self._lock:
            return self._peer_latencies.get(peer_id)

    def calculate_decayed_ttl(
        self, current_ttl: int, queue_depth: int, downstream_peer_id: Optional[str] = None
    ) -> int:
        """Calculates the adaptive TTL for forwarding a message based on local congestion"""
        if current_ttl <= 0:
            return 0

        penalty = 1
        if queue_depth >= self.config.queue_congestion_threshold:
            penalty += self.config.decay_penalty

        if downstream_peer_id:
            latency = self.get_peer_latency(downstream_peer_id)
            if latency is not None and latency >= self.config.latency_congestion_threshold_sec:
                penalty += self.config.poison_reverse_penalty

        new_ttl = current_ttl - penalty
        return max(self.config.min_ttl, new_ttl) if new_ttl > 0 else 0

    def should_drop(self, current_ttl: int, queue_depth: int, downstream_peer_id: Optional[str] = None) -> bool:
        """Determines if a message should be dropped due to TTL exhaustion."""
        return self.calculate_decayed_ttl(current_ttl, queue_depth, downstream_peer_id) <= 0

    def reset(self) -> None:
        """Resets all internal peer latency states."""
        with self._lock:
            self._peer_latencies.clear()
