import threading
import time
from typing import Dict, Set, Tuple, Optional, Any


class TombstoneGarbageCollector:
    """
    Garbage Collector for Delta-State OR-Set CRDT tombstones to prune acknowledged deletions
    and reclaim memory across decentralized peers.
    """

    def __init__(self, ttl_seconds: float = 300.0):
        self.ttl_seconds = ttl_seconds
        # element -> (removed_tags_set, timestamp_removed)
        self._tombstones: Dict[Any, Tuple[Set[Tuple[str, str]], float]] = {}
        self._lock = threading.Lock()

    def record_tombstones(self, tombstones: Dict[Any, Set[Tuple[str, str]]]) -> None:
        with self._lock:
            now = time.time()
            for elem, tags in tombstones.items():
                if elem not in self._tombstones:
                    self._tombstones[elem] = (set(), now)
                self._tombstones[elem][0].update(tags)

    def sweep(self) -> Set[Any]:
        """Removes tombstones older than TTL and returns pruned elements."""
        with self._lock:
            now = time.time()
            expired_elements = set()
            for elem, (_, removed_at) in list(self._tombstones.items()):
                if now - removed_at > self.ttl_seconds:
                    expired_elements.add(elem)
                    del self._tombstones[elem]
            return expired_elements

    def get_tombstone_state(self) -> Dict[Any, Set[Tuple[str, str]]]:
        with self._lock:
            return {elem: set(tags) for elem, (tags, _) in self._tombstones.items()}
