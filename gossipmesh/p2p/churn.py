"""Entropy-Based Peer Churn Defense and Sybil Mitigation module (GossipMesh P2P Subsystem).
Provides sliding-window entropy calculation over incoming peer message metadata to detect and penalize
Sybil nodes flooding fake heartbeat or vector clock vectors.
"""

import math
import time
import threading
from collections import deque
from typing import Dict, List, Optional, Tuple, Any
from gossipmesh.p2p.entropy import compute_shannon_entropy


class ChurnDefenseConfig:
    """Configuration parameters for entropy-based churn defense and Sybil mitigation."""

    def __init__(
        self,
        window_size: int = 50,
        entropy_variance_threshold: float = 0.2,
        max_allowed_ticks_variance_exceeded: int = 3,
        quarantine_duration_sec: float = 300.0,
    ) -> None:
        self.window_size = window_size
        self.entropy_variance_threshold = entropy_variance_threshold
        self.max_allowed_ticks_variance_exceeded = max_allowed_ticks_variance_exceeded
        self.quarantine_duration_sec = quarantine_duration_sec


class PeerChurnTracker:
    """Tracks sliding-window entropy of peer message metadata to detect Sybil flooding.
    Bounded memory via deque with strict concurrency safety.
    """

    def __init__(self, peer_id: str, config: Optional[ChurnDefenseConfig] = None) -> None:
        self.peer_id = peer_id
        self.config = config or ChurnDefenseConfig()
        self._entropy_window: deque = deque(maxlen=self.config.window_size)
        self._ticks_exceeded = 0
        self._quarantined_until = 0.0
        self._lock = threading.Lock()

    def record_heartbeat_metadata(self, metadata_vector: Dict[str, int]) -> float:
        """Record metadata vector, compute entropy, and update sliding window. Returns computed entropy."""
        entropy = compute_shannon_entropy(metadata_vector)
        with self._lock:
            self._entropy_window.append(entropy)
        return float(entropy)

    def evaluate_churn_defense(self) -> Tuple[bool, float]:
        """Evaluate sliding window entropy variance against the threshold.
        Returns a tuple of (is_sybil_flagged, current_variance).
        """
        with self._lock:
            if len(self._entropy_window) < 5:
                return False, 0.0

            values = list(self._entropy_window)
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)

            if variance < self.config.entropy_variance_threshold:
                self._ticks_exceeded += 1
                if self._ticks_exceeded >= self.config.max_allowed_ticks_variance_exceeded:
                    self._quarantined_until = time.time() + self.config.quarantine_duration_sec
                    return True, float(variance)
            else:
                # Reset or decay violations if entropy variance is normal
                if self._ticks_exceeded > 0:
                    self._ticks_exceeded -= 1

            return False, float(variance)

    def is_quarantined(self) -> bool:
        """Check if peer is currently quarantined due to churn/Sybil detection."""
        with self._lock:
            if self._quarantined_until == 0.0:
                return False
            if time.time() > self._quarantined_until:
                self._quarantined_until = 0.0
                self._ticks_exceeded = 0
                return False
            return True

    def reset(self) -> None:
        """Reset internal state and clear history."""
        with self._lock:
            self._entropy_window.clear()
            self._ticks_exceeded = 0
            self._quarantined_until = 0.0


class MeshChurnManager:
    """Manages peer churn trackers across the local mesh node."""

    def __init__(self, config: Optional[ChurnDefenseConfig] = None) -> None:
        self.config = config or ChurnDefenseConfig()
        self._trackers: Dict[str, PeerChurnTracker] = {}
        self._lock = threading.Lock()

    def _get_or_create_tracker(self, peer_id: str) -> PeerChurnTracker:
        with self._lock:
            if peer_id not in self._trackers:
                self._trackers[peer_id] = PeerChurnTracker(peer_id, self.config)
            return self._trackers[peer_id]

    def process_heartbeat(self, peer_id: str, metadata_vector: Dict[str, int]) -> Tuple[bool, float]:
        """Ingests a peer heartbeat vector, updates sliding window, and evaluates Sybil churn defense."""
        tracker = self._get_or_create_tracker(peer_id)
        tracker.record_heartbeat_metadata(metadata_vector)
        is_sybil, variance = tracker.evaluate_churn_defense()
        return is_sybil, variance

    def is_peer_quarantined(self, peer_id: str) -> bool:
        with self._lock:
            tracker = self._trackers.get(peer_id)
            if not tracker:
                return False
        return tracker.is_quarantined()
