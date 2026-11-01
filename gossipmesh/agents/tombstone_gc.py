import threading
from typing import Any, Dict, Set, Tuple
from gossipmesh.core.clocks import VectorClock


class TombstoneGarbageCollector:
    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self.ttl_seconds = ttl_seconds
        self.tombstones: Dict[str, Tuple[float, VectorClock]] = {}
        self._lock = threading.Lock()

    def mark_deleted(self, key: str, clock: VectorClock) -> None:
        import time

        with self._lock:
            self.tombstones[key] = (time.time(), clock)

    def is_deleted(self, key: str) -> bool:
        with self._lock:
            return key in self.tombstones

    def sweep(self) -> int:
        import time

        now = time.time()
        removed = 0
        with self._lock:
            expired = [k for k, (ts, _) in self.tombstones.items() if now - ts > self.ttl_seconds]
            for k in expired:
                del self.tombstones[k]
                removed += 1
        return removed
