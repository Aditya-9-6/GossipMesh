"""
Decentralized adaptive heartbeat backoff mechanism for gossip mesh consensus nodes.
Dynamically adjusts ping intervals based on rolling network latency and partition heuristics.
"""

from __future__ import annotations

import math
import time
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AdaptiveBackoffCalculator:
    """
    Calculates dynamic backoff intervals for node heartbeats based on rolling network
    latency statistics and partition detection heuristics.
    """

    def __init__(
        self,
        base_interval: float = 1.0,
        min_interval: float = 0.2,
        max_interval: float = 30.0,
        backoff_multiplier: float = 1.5,
        jitter_factor: float = 0.1,
    ):
        self.base_interval = base_interval
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.backoff_multiplier = backoff_multiplier
        self.jitter_factor = jitter_factor

    def compute_backoff(
        self,
        consecutive_failures: int,
        rolling_avg_latency: float,
        partition_detected: bool = False,
    ) -> float:
        """
        Computes the next heartbeat interval given failure counts, latency, and partition status.
        """
        if partition_detected:
            # Aggressively back off during partition to prevent message flooding
            interval = self.max_interval
        elif consecutive_failures == 0:
            # Healthy state: tie interval to rolling latency with base scaling
            interval = max(
                self.min_interval,
                min(
                    self.base_interval,
                    rolling_avg_latency * 2.0 if rolling_avg_latency > 0 else self.base_interval,
                ),
            )
        else:
            # Exponential backoff with failures
            interval = self.base_interval * (self.backoff_multiplier**consecutive_failures)
            interval = min(self.max_interval, max(self.min_interval, interval))

        return float(interval)
