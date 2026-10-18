import time
import threading
from typing import Dict, Optional, Tuple

class DedupCache:
    """Thread-safe message deduplication cache using a fixed-capacity ring buffer
    and amortized TTL-based expiration index for O(1) insertion and O(1) lookup.
    """
    def __init__(self, capacity: int = 10000, default_ttl: float = 60.0):
        self.capacity = max(1, capacity)
        self.default_ttl = default_ttl
        self._lock = threading.Lock()
        self._buffer: list[Optional[Tuple[str, float]]] = [None] * self.capacity
        self._index: Dict[str, int] = {}
        self._head = 0
        self._tail = 0
        self._size = 0

    def _evict_expired(self, current_time: float) -> None:
        """Internal helper to evict expired items from the tail of the ring buffer."""
        while self._size > 0:
            item = self._buffer[self._tail]
            if item is None:
                self._tail = (self._tail + 1) % self.capacity
                self._size -= 1
                continue
            msg_id, expire_at = item
            if expire_at <= current_time:
                self._index.pop(msg_id, None)
                self._buffer[self._tail] = None
                self._tail = (self._tail + 1) % self.capacity
                self._size -= 1
            else:
                break

    def check_and_add(self, message_id: str, ttl: Optional[float] = None) -> bool:
        """Checks if a message ID is already present and valid. If not, adds it.
        Returns True if the message is NEW (not a duplicate), False otherwise.
        """
        if not message_id:
            return False

        now = time.time()
        effective_ttl = ttl if ttl is not None else self.default_ttl
        expire_at = now + effective_ttl

        with self._lock:
            self._evict_expired(now)

            if message_id in self._index:
                idx = self._index[message_id]
                item = self._buffer[idx]
                if item is not None and item[1] > now:
                    return False
                else:
                    self._index.pop(message_id, None)

            if self._size >= self.capacity:
                old_item = self._buffer[self._tail]
                if old_item is not None:
                    self._index.pop(old_item[0], None)
                self._buffer[self._tail] = None
                self._tail = (self._tail + 1) % self.capacity
                self._size -= 1

            self._buffer[self._head] = (message_id, expire_at)
            self._index[message_id] = self._head
            self._head = (self._head + 1) % self.capacity
            self._size += 1
            return True

    def contains(self, message_id: str) -> bool:
        """Checks if a message ID exists and has not expired, without modifying state."""
        if not message_id:
            return False

        now = time.time()
        with self._lock:
            self._evict_expired(now)
            if message_id not in self._index:
                return False
            idx = self._index[message_id]
            item = self._buffer[idx]
            if item is None or item[1] <= now:
                return False
            return True

    def clear(self) -> None:
        """Clears all entries in the dedup cache."""
        with self._lock:
            self._buffer = [None] * self.capacity
            self._index.clear()
            self._head = 0
            self._tail = 0
            self._size = 0
