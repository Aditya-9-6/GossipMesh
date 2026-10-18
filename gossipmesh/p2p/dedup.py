import time
import threading
from typing import Optional, Dict, Any


class CountingBloomFilter:
    """A memory-efficient counting Bloom filter for approximate membership testing and O(1) duplicate packet rejection."""
    
    def __init__(self, capacity: int = 10000, error_rate: float = 0.01) -> None:
        self.capacity = capacity
        self.error_rate = error_rate
        # Simple bit array / integer counter array representation
        self.size = max(1000, int(-capacity * (error_rate ** 0.5) / (0.693 ** 2)))
        self.num_hashes = max(1, int((self.size / capacity) * 0.693))
        self.table = [0] * self.size
        self._lock = threading.Lock()

    def _hashes(self, item: str) -> list[int]:
        h1 = hash(item)
        h2 = hash(item[::-1])
        return [(abs(h1 + i * h2) % self.size) for i in range(self.num_hashes)]

    def add(self, item: str) -> None:
        with self._lock:
            for idx in self._hashes(item):
                if self.table[idx] < 255:
                    self.table[idx] += 1

    def remove(self, item: str) -> None:
        with self._lock:
            for idx in self._hashes(item):
                if self.table[idx] > 0:
                    self.table[idx] -= 1

    def __contains__(self, item: str) -> bool:
        with self._lock:
            return all(self.table[idx] > 0 for idx in self._hashes(item))


class BoundedLRUGossipRingBuffer:
    """High-performance memory-bounded LRU message ring-buffer with Bloom filter deduplication."""

    def __init__(self, capacity: int = 1000) -> None:
        self.capacity = capacity
        self.cache: dict[str, Any] = {}
        self.bloom = CountingBloomFilter(capacity=capacity)
        self._lock = threading.Lock()

    def put(self, message_id: str, payload: Any) -> Optional[tuple[str, Any]]:
        """Adds a message ID and payload. Evicts the oldest item if capacity is exceeded. Returns evicted item if any."""
        with self._lock:
            evicted = None
            if message_id in self.cache:
                # Update LRU order
                self.cache.move_to_end(message_id)
                self.cache[message_id] = payload
                return None

            if len(self.cache) >= self.capacity:
                oldest_id, oldest_payload = self.cache.popitem(last=False)
                self.bloom.remove(oldest_id)
                evicted = (oldest_id, oldest_payload)

            self.cache[message_id] = payload
            self.bloom.add(message_id)
            return evicted

    def get(self, message_id: str) -> Optional[Any]:
        with self._lock:
            if message_id not in self.cache:
                return None
            self.cache.move_to_end(message_id)
            return self.cache[message_id]

    def __contains__(self, message_id: str) -> bool:
        return message_id in self.bloom

    def __len__(self) -> int:
        with self._lock:
            return len(self.cache)
