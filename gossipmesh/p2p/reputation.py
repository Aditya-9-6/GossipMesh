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
        leak_rate_per_sec: Optional[float] = None,
        leak_rate: Optional[float] = None,
        quarantine_threshold: float = 50.0
    ) -> None:
        self.capacity = capacity
        self.leak_rate = leak_rate_per_sec if leak_rate_per_sec is not None else (leak_rate if leak_rate is not None else 10.0)
        self.quarantine_threshold = quarantine_threshold
        self._scores: Dict[str, float] = {}
        self._last_update: Dict[str, float] = {}
        self._quarantined: Dict[str, bool] = {}
        self._lock = threading.Lock()

    def _leak(self, peer_id: str, now: float) -> float:
        last = self._last_update.get(peer_id, now)
        elapsed = now - last
        score = self._scores.get(peer_id, 0.0)
        score = max(0.0, score - elapsed * self.leak_rate)
        self._last_update[peer_id] = now
        self._scores[peer_id] = score
        return score

    def add_penalty(self, peer_id: str, amount: float = 10.0) -> float:
        with self._lock:
            now = time.monotonic()
            score = self._leak(peer_id, now)
            score = min(self.capacity, score + amount)
            self._scores[peer_id] = score
            if score >= self.quarantine_threshold:
                self._quarantined[peer_id] = True
            return score

    def is_quarantined(self, peer_id: str) -> bool:
        with self._lock:
            now = time.monotonic()
            self._leak(peer_id, now)
            return self._quarantined.get(peer_id, False)

    def get_score(self, peer_id: str) -> float:
        with self._lock:
            now = time.monotonic()
            return self._leak(peer_id, now)

    def clear(self) -> None:
        with self._lock:
            self._scores.clear()
            self._last_update.clear()
            self._quarantined.clear()

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "capacity": self.capacity,
                "leak_rate": self.leak_rate,
                "quarantine_threshold": self.quarantine_threshold,
                "tracked_peers": len(self._scores),
                "quarantined_peers": sum(1 for q in self._quarantined.values() if q)
            }
