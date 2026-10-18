import time
import threading
from collections import OrderedDict
from typing import Optional, Any

class LRUDigestCache:
    """High-performance, memory-bounded Least Recently Used (LRU) cache
    with time-to-live (TTL) expiry for tracking seen gossip message IDs."""
    
    def __init__(self, max_size: int = 10000, default_ttl: float = 86400.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()

    def _evict_expired(self, now: float):
        keys_to_delete = []
        for k, expiry in self._cache.items():
            if expiry <= now:
                keys_to_delete.append(k)
            else:
                break
        for k in keys_to_delete:
            self._cache.pop(k, None)

    def add(self, message_id: str, ttl: Optional[float] = None) -> None:
        now = time.time()
        expiry = now + (ttl if ttl is not None else self.default_ttl)
        with self._lock:
            self._evict_expired(now)
            if message_id in self._cache:
                self._cache.move_to_end(message_id)
            self._cache[message_id] = expiry
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def contains(self, message_id: str) -> bool:
        now = time.time()
        with self._lock:
            self._evict_expired(now)
            expiry = self._cache.get(message_id)
            if expiry is None:
                return False
            if expiry <= now:
                self._cache.pop(message_id, None)
                return False
            self._cache.move_to_end(message_id)
            return True

    def __contains__(self, message_id: str) -> bool:
        return self.contains(message_id)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        now = time.time()
        with self._lock:
            self._evict_expired(now)
            return len(self._cache)
