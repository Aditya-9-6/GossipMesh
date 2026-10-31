"""
Decentralized adaptive heartbeat backoff engine for partition detection and message flooding prevention.
"""

from __future__ import annotations

import math
import random
import time
from typing import Dict, List, Optional


class AdaptiveBackoffConfig:
    def __init__(
        self,
        base_interval: float = 1.0,
        min_interval: float = 0.2,
        max_interval: float = 30.0,
        backoff_factor: float = 2.0,
        jitter_factor: float = 0.1,
        partition_threshold_failures: int = 3,
    ):
        self.base_interval = base_interval
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.backoff_factor = backoff_factor
        self.jitter_factor = jitter_factor
        self.partition_threshold_failures = partition_threshold_failures


class NodeHeartbackoffState:
    def __init__(self, node_id: str, config: Optional[AdaptiveBackoffConfig] = None):
        self.node_id = node_id
        self.config = config or AdaptiveBackoffConfig()
        self.current_interval = self.config.base_interval
        self.consecutive_failures = 0
        self.last_ping_time = 0.0
        self.last_ack_time = 0.0
        self.rolling_latencies: List[float] = []
        self.max_latency_samples = 10
        self.is_partitioned = False

    def record_success(self, latency: float, now: Optional[float] = None) -> float:
        t = now if now is not None else time.time()
        self.last_ack_time = t
        self.consecutive_failures = 0
        self.is_partitioned = False

        self.rolling_latencies.append(latency)
        if len(self.rolling_latencies) > self.max_latency_samples:
            self.rolling_latencies.pop(0)

        # Rapid convergence upon healing: reset or scale down towards base/min interval based on latency
        avg_latency = sum(self.rolling_latencies) / len(self.rolling_latencies)
        target = max(self.config.min_interval, self.config.base_interval + (avg_latency * 0.5))
        self.current_interval = max(self.config.min_interval, min(target, self.config.max_interval))
        return self.current_interval

    def record_failure(self, now: Optional[float] = None) -> float:
        t = now if now is not None else time.time()
        self.last_ping_time = t
        self.consecutive_failures += 1

        if self.consecutive_failures >= self.config.partition_threshold_failures:
            self.is_partitioned = True

        # Exponential backoff with jitter
        backoff = self.current_interval * self.config.backoff_factor
        jitter = backoff * self.config.jitter_factor * (random.random() * 2 - 1)
        self.current_interval = max(self.config.min_interval, min(backoff + jitter, self.config.max_interval))
        return self.current_interval

    def get_current_interval(self) -> float:
        return self.current_interval
