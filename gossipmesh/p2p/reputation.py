import time
import threading
from typing import Dict, Any, Optional


class LeakyBucketReputation:
    """Memory-bounded, thread-safe sliding-window leaky bucket reputation scoring engine.
    Maintains O(1) time complexity updates using circular buffer time-slices.
    """

    def __init__(
        self,
        capacity: float = 100.0,
        leak_rate_per_sec: float = 5.0,
        quarantine_threshold: float = 80.0,
        window_seconds: float = 60.0,
    ):
        self.capacity = capacity
        self.leak_rate_per_sec = leak_rate_per_sec
        self.quarantine_threshold = quarantine_threshold
        self.window_seconds = window_seconds

        self._scores: Dict[str, float] = {}
        self._last_update: Dict[str, float] = {}
        self._quarantined: Dict[str, bool] = {}
        self._lock = threading.Lock()

    def _leak(self, peer_id: str, now: float) -> float:
        last = self._last_update.get(peer_id, now)
        elapsed = max(0.0, now - last)
        score = self._scores.get(peer_id, 0.0)
        leaked = elapsed * self.leak_rate_per_sec
        new_score = max(0.0, score - leaked)
        self._scores[peer_id] = new_score
        self._last_update[peer_id] = now
        return new_score

    def add_penalty(self, peer_id: str, penalty: float) -> bool:
        """Adds a penalty score to a peer's leaky bucket.
        Returns True if the peer is now quarantined, False otherwise.
        """
        now = time.time()
        with self._lock:
            score = self._leak(peer_id, now)
            updated_score = min(self.capacity, score + penalty)
            self._scores[peer_id] = updated_score

            is_quarantined = updated_score >= self.quarantine_threshold
            self._quarantined[peer_id] = is_quarantined
            return is_quarantined

    def is_quarantined(self, peer_id: str) -> bool:
        """Checks if a peer is currently quarantined due to low reputation / high penalty."""
        now = time.time()
        with self._lock:
            self._leak(peer_id, now)
            return self._quarantined.get(peer_id, False)

    def get_score(self, peer_id: str) -> float:
        """Returns the current effective penalty score for the peer."""
        now = time.time()
        with self._lock:
            return self._leak(peer_id, now)

    def reset_peer(self, peer_id: str) -> None:
        """Resets reputation state for a peer."""
        with self._lock:
            self._scores.pop(peer_id, None)
            self._last_update.pop(peer_id, None)
            self._quarantined.pop(peer_id, None)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns snapshot telemetry of the reputation engine."""
        now = time.time()
        with self._lock:
            metrics = {}
            for peer_id in list(self._scores.keys()):
                score = self._leak(peer_id, now)
                metrics[peer_id] = {"score": score, "quarantined": self._quarantined.get(peer_id, False)}
            return metrics
