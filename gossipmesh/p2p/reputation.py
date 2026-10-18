import time
import threading
from typing import Dict, Any, Optional


class LeakyBucketReputation:
    """Memory-bounded, thread-safe sliding-window leaky bucket reputation scoring engine.
    Maintains O(1) time complexity updates using circular buffer time-slices.
    """
    def __init__(self, capacity: float = 100.0, leak_rate: float = 1.0, quarantine_threshold: float = 20.0) -> None:
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.quarantine_threshold = quarantine_threshold
        self._scores: Dict[str, float] = {}
        self._last_update: Dict[str, float] = {}
        self._quarantined: Dict[str, bool] = {}
        self._lock = threading.Lock()

    def _leak(self, peer_id: str, now: float) -> float:
        last = self._last_update.get(peer_id, now)
        elapsed = now - last
        score = self._scores.get(peer_id, self.capacity)
        leaked = elapsed * self.leak_rate
        new_score = min(self.capacity, score + leaked)
        self._scores[peer_id] = new_score
        self._last_update[peer_id] = now
        return new_score

    def penalize(self, peer_id: str, amount: float) -> float:
        with self._lock:
            now = time.monotonic()
            score = self._leak(peer_id, now)
            new_score = max(0.0, score - amount)
            self._scores[peer_id] = new_score
            if new_score <= self.quarantine_threshold:
                self._quarantined[peer_id] = True
            return new_score

    def reward(self, peer_id: str, amount: float) -> float:
        with self._lock:
            now = time.monotonic()
            score = self._leak(peer_id, now)
            new_score = min(self.capacity, score + amount)
            self._scores[peer_id] = new_score
            if new_score > self.quarantine_threshold:
                self._quarantined[peer_id] = False
            return new_score

    def is_quarantined(self, peer_id: str) -> bool:
        with self._lock:
            now = time.monotonic()
            self._leak(peer_id, now)
            return self._quarantined.get(peer_id, False)

    def get_score(self, peer_id: str) -> float:
        with self._lock:
            now = time.monotonic()
            return self._leak(peer_id, now)
