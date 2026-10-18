import time
import math
from typing import Dict, Any, List

class AdaptiveBackoffController:
    """Calculates exponential backoff and dynamic heartbeat intervals based on rolling latency."""
    def __init__(self, base_interval: float = 1.0, max_interval: float = 60.0, multiplier: float = 2.0, jitter: float = 0.1):
        self.base_interval = base_interval
        self.max_interval = max_interval
        self.multiplier = multiplier
        self.jitter = jitter
        self._failure_counts: Dict[str, int] = {}
        self._latencies: Dict[str, List[float]] = {}

    def record_success(self, node_id: str, latency: float):
        self._failure_counts[node_id] = 0
        if node_id not in self._latencies:
            self._latencies[node_id] = []
        buf = self._latencies[node_id]
        buf.append(latency)
        if len(buf) > 20:
            buf.pop(0)

    def record_failure(self, node_id: str):
        self._failure_counts[node_id] = self._failure_counts.get(node_id, 0) + 1

    def get_backoff_interval(self, node_id: str) -> float:
        failures = self._failure_counts.get(node_id, 0)
        if failures == 0:
            return self.base_interval
        interval = self.base_interval * (self.multiplier ** (failures - 1))
        return min(self.max_interval, interval)

    def get_smoothed_latency(self, node_id: str) -> float:
        buf = self._latencies.get(node_id, [])
        if not buf:
            return 0.0
        return sum(buf) / len(buf)

    def is_partitioned(self, node_id: str, threshold: float = 5.0) -> bool:
        failures = self._failure_counts.get(node_id, 0)
        if failures >= 3:
            return True
        smoothed = self.get_smoothed_latency(node_id)
        if smoothed > threshold:
            return True
        return False
