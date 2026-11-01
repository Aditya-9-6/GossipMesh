"""Entropy-Based Peer Churn Defense and Sybil Mitigation module for GossipMesh P2P network."""

import math
import time
from collections import deque
from typing import Dict, List, Tuple, Any, Optional


class ChurnDefenseConfig:
    """Configuration parameters for entropy-based peer churn and Sybil mitigation."""
    def __init__(
        self, 
        window_size: int = 50,
        entropy_variance_threshold: float = 2.5,
        max_ticks_to_drop: int = 3,
        min_samples_for_evaluation: int = 10
    ) -> None:
        self.window_size = window_size
        self.entropy_variance_threshold = entropy_variance_threshold
        self.max_ticks_to_drop = max_ticks_to_drop
        self.min_samples_for_evaluation = min_samples_for_evaluation


class PeerChurnDefenseEngine:
    """Tracks sliding-window entropy of peer heartbeat vectors to detect and penalize Sybil flood."""
    
    def __init__(self, config: Optional[ChurnDefenseConfig] = None) -> None:
        self.config = config or ChurnDefenseConfig()
        self._peer_entropy_windows: Dict[str, deque] = {}
        self._peer_violation_ticks: Dict[str, int] = {}

    def _get_window(self, peer_id: str) -> deque:
        if peer_id not in self._peer_entropy_windows:
            self._peer_entropy_windows[peer_id] = deque(maxlen=self.config.window_size)
        return self._peer_entropy_windows[peer_id]

    def record_heartbeat(self, peer_id: str, heartbeat_vector: Dict[str, int]) -> float:
        """Calculates shannon entropy of a heartbeat vector and records it in sliding window."""
        entropy = self._compute_shannon_entropy(heartbeat_vector)
        window = self._get_window(peer_id)
        window.append(entropy)
        return entropy

    def evaluate_peer(self, peer_id: str) -> Tuple[bool, str]:
        """
        Evaluates if peer exceeds entropy variance thresholds.
        Returns (should_drop, reason).
        """
        window = self._get_window(peer_id)
        if len(window) < self.config.min_samples_for_evaluation:
            return False, "Insufficient samples"

        variance = self._compute_variance(list(window))
        
        if variance > self.config.entropy_variance_threshold:
            ticks = self._peer_violation_ticks.get(peer_id, 0) + 1
            self._peer_violation_ticks[peer_id] = ticks
            if ticks >= self.config.max_ticks_to_drop:
                return True, f"Sybil detected: variance {variance:.2f} exceeded threshold across {ticks} ticks"
            return False, f"Warning: high variance {variance:.2f} (tick {ticks})"
        else:
            # Decay violation ticks on stable behavior
            if peer_id in self._peer_violation_ticks:
                self._peer_violation_ticks[peer_id] = max(0, self._peer_violation_ticks[peer_id] - 1)
            return False, "Normal"

    @staticmethod
    def _compute_shannon_entropy(vector: Dict[str, int]) -> float:
        if not vector:
            return 0.0
        total = sum(vector.values())
        if total == 0:
            return 0.0
        entropy = 0.0
        for val in vector.values():
            if val > 0:
                p = val / total
                entropy -= p * math.log2(p)
        return float(entropy)

    @staticmethod
    def _compute_variance(values: List[float]) -> float:
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return float(variance)
