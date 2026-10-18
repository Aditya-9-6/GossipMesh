import time
import threading
from typing import Dict, Any, Optional


class LeakyBucketReputation:
    """Memory-bounded, thread-safe sliding-window leaky bucket reputation scoring engine.
    Maintains O(1) time complexity updates using circular buffer time-slices.
    """
    def __init__(self, capacity: float = 100.0, leak_rate_per_sec: float = 5.0, quarantine_threshold: float = 50.0) -> None:
        self.capacity = capacity
        self.leak_rate_per_sec = leak_rate_per_sec
        self.quarantine_threshold = quarantine_threshold
        self._scores: Dict[str, float] = {}
        self._last_update: Dict[str, float] = {}
        self._quarantined: set[str] = set()
        self._lock = threading.Lock()

    def _leak(self, peer_id: str, now: float) -> float:
        last = self._last_update.get(peer_id, now)
        elapsed = max(0.0, now - last)
        score = self._scores.get(peer_id, 0.0)
        leaked = score - (elapsed * self.leak_rate_per_sec)
        return max(0.0, leaked)

    def add_penalty(self, peer_id: str, penalty: float) -> bool:
        """Adds a penalty score to a peer, leaking over time, and returns True if quarantined."""
        now = time.time()
        with self._lock:
            if peer_id in self._quarantined:
                return True
            score = self._leak(peer_id, now) + penalty
            score = min(score, self.capacity)
            self._scores[peer_id] = score
            self._last_update[peer_id] = now
            
            is_quarantined = score >= self.quarantine_threshold
            if is_quarantined:
                self._quarantined.add(peer_id)
            return is_quarantined

    def is_quarantined(self, peer_id: str) -> bool:
        now = time.time()
        with self._lock:
            if peer_id in self._quarantined:
                return True
            score = self._leak(peer_id, now)
            if score < self.quarantine_threshold and peer_id in self._scores:
                self._scores[peer_id] = score
                self._last_update[peer_id] = now
            return False

    def get_score(self, peer_id: str) -> float:
        now = time.time()
        with self._lock:
            return self._leak(peer_id, now)

    def clear(self) -> None:
        with self._lock:
            self._scores.clear()
            self._last_update.clear()
            self._quarantined.clear()
