import threading
from typing import Dict, Set, Tuple, Any
from gossipmesh.core.clocks import VectorClock


class TombstoneGarbageCollector:
    def __init__(self, ttl_seconds: float = 86400.0):
        self.ttl_seconds = ttl_seconds
        self._tombstones: Dict[str, float] = {}
        self._lock = threading.Lock()

    def add(self, key: str, timestamp: float) -> None:
        with self._lock:
            self._tombstones[key] = timestamp

    def collect(self, current_time: float) -> Set[str]:
        with self._lock:
            expired = {k for k, ts in self._tombstones.items() if current_time - ts > self.ttl_seconds}
            for k in expired:
                del self._tombstones[k]
            return expired
