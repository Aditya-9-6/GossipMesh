"""High-performance deduplication utilities including CountingBloomFilter and BoundedLRUGossipRingBuffer."""

import zlib
import threading
from typing import Any, Dict, Optional, Set


class CountingBloomFilter:
    """Counting Bloom Filter for message ID deduplication and removal."""

    def __init__(self, capacity: int = 1000, error_rate: float = 0.01) -> None:
        self.capacity = capacity
        self.error_rate = error_rate
        self.size = max(1000, capacity * 10)
        self._counters = [0] * self.size
        self._lock = threading.Lock()

    def _hashes(self, item: str) -> list[int]:
        encoded = item.encode("utf-8")
        h1 = zlib.crc32(encoded)
        h2 = zlib.adler32(encoded)
        return [(h1 + i * h2) % self.size for i in range(3)]

    async def add(self, item: str) -> None:
        with self._lock:
            for idx in self._hashes(item):
                self._counters[idx] += 1

    async def remove(self, item: str) -> None:
        with self._lock:
            for idx in self._hashes(item):
                if self._counters[idx] > 0:
                    self._counters[idx] -= 1

    def __contains__(self, item: str) -> bool:
        with self._lock:
            for idx in self._hashes(item):
                if self._counters[idx] == 0:
                    return False
            return True


class BoundedLRUGossipRingBuffer:
    """Bounded LRU ring buffer for gossip state message deduplication."""

    def __init__(self, max_capacity: int = 100, bloom_capacity: int = 1000) -> None:
        self.max_capacity = max_capacity
        self._store: Dict[str, Any] = {}
        self._order: list[str] = []
        self._bloom = CountingBloomFilter(capacity=bloom_capacity)
        self._lock = threading.Lock()

    async def add(self, key: str, value: Any) -> Optional[Any]:
        with self._lock:
            evicted_val = None
            if key in self._store:
                self._order.remove(key)
            elif len(self._store) >= self.max_capacity:
                oldest_key = self._order.pop(0)
                evicted_val = self._store.pop(oldest_key)

            self._store[key] = value
            self._order.append(key)
        await self._bloom.add(key)
        return evicted_val

    async def contains(self, key: str) -> bool:
        return key in self._bloom

    async def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._store:
                return None
            self._order.remove(key)
            self._order.append(key)
            return self._store[key]

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
