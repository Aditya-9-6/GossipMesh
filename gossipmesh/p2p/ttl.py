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
    """Manages adaptive TTL reduction and poison-reverse heuristics based on local queue depths and downstream peer latencies."""

    def __init__(self, config: Optional[TTLConfig] = None) -> None:
        self.config = config or TTLConfig()
        self._latencies: Dict[str, float] = {}
        self._lock = threading.Lock()

    def update_peer_latency(self, peer_id: str, latency_sec: float) -> None:
        if not peer_id:
            raise ValueError("peer_id must not be empty")
        if latency_sec < 0:
            raise ValueError("latency must be non-negative")
        with self._lock:
            self._latencies[peer_id] = latency_sec

    def compute_ttl(self, peer_id: str, queue_depth: int, initial_ttl: Optional[int] = None) -> int:
        base = initial_ttl if initial_ttl is not None else self.config.base_ttl
        penalty = 0

        if queue_depth >= self.config.queue_congestion_threshold:
            penalty += self.config.decay_penalty

        with self._lock:
            latency = self._latencies.get(peer_id, 0.0)

        if latency >= self.config.latency_congestion_threshold_sec:
            penalty += self.config.poison_reverse_penalty

        computed = base - penalty
        return max(self.config.min_ttl, computed)

    def reset(self) -> None:
        with self._lock:
            self._latencies.clear()
