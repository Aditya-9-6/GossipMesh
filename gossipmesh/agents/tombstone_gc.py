import threading
from typing import Dict, Set, Tuple, Any
from gossipmesh.core.clocks import VectorClock


class TombstoneGarbageCollector:
    def __init__(self, ttl_seconds: float = 300.0):
        self.ttl_seconds = ttl_seconds
        self._tombstones: Dict[str, float] = {}
        self._lock = threading.Lock()

    def add(self, entity_id: str, timestamp: float) -> None:
        with self._lock:
            self._tombstones[entity_id] = timestamp

    def is_expired(self, entity_id: str, current_time: float) -> bool:
        with self._lock:
            ts = self._tombstones.get(entity_id)
            if ts is None:
                return False
            return (current_time - ts) > self.ttl_seconds

    def sweep(self, current_time: float) -> Set[str]:
        with self._lock:
            expired = {eid for eid, ts in self._tombstones.items() if (current_time - ts) > self.ttl_seconds}
            for eid in expired:
                del self._tombstones[eid]
            return expired
