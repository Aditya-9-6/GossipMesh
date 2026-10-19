import time
import threading
from typing import Optional, Dict


class RingBufferDedup:
    """High-throughput, thread-safe message deduplication cache using a fixed-capacity ring buffer
    combined with an amortized TTL-based expiration index for O(1) insertion and lookup.
    """

    def __init__(self, capacity: int = 10000, default_ttl: float = 60.0):
        self.capacity = capacity
        self.default_ttl = default_ttl
        self._lock = threading.Lock()
        self._buffer: list[Optional[str]] = [None] * capacity
        self._timestamps: list[float] = [0.0] * capacity
        self._index: Dict[str, int] = {}
        self._head = 0
        self._tail = 0
        self._size = 0

    def _evict_expired(self, current_time: float) -> None:
        while self._size > 0:
            oldest_msg = self._buffer[self._tail]
            oldest_time = self._timestamps[self._tail]
            if oldest_msg is not None and current_time - oldest_time > self.default_ttl:
                self._index.pop(oldest_msg, None)
                self._buffer[self._tail] = None
                self._timestamps[self._tail] = 0.0
                self._tail = (self._tail + 1) % self.capacity
                self._size -= 1
            else:
                break

    def check_and_add(self, message_id: str, ttl: Optional[float] = None) -> bool:
        """Checks if message_id is already seen. If not, adds it and returns True (new).
        If already present or recently expired, returns False (duplicate).
        """
        with self._lock:
            now = time.time()
            effective_ttl = ttl if ttl is not None else self.default_ttl

            self._evict_expired(now)

            if message_id in self._index:
                idx = self._index[message_id]
                if now - self._timestamps[idx] <= effective_ttl:
                    return False
                else:
                    pass

            if self._size == self.capacity:
                evicted_msg = self._buffer[self._head]
                if evicted_msg is not None:
                    self._index.pop(evicted_msg, None)
                self._tail = (self._tail + 1) % self.capacity
                self._size -= 1

            self._buffer[self._head] = message_id
            self._timestamps[self._head] = now
            self._index[message_id] = self._head
            self._head = (self._head + 1) % self.capacity
            self._size += 1
            return True

    def contains(self, message_id: str) -> bool:
        """O(1) lookup to check if a message_id is currently tracked and not expired."""
        with self._lock:
            now = time.time()
            self._evict_expired(now)
            if message_id not in self._index:
                return False
            idx = self._index[message_id]
            return (now - self._timestamps[idx]) <= self.default_ttl

    def size(self) -> int:
        with self._lock:
            self._evict_expired(time.time())
            return self._size
