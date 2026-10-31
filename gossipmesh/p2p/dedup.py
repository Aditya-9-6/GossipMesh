import asyncio
import hashlib
import math
from typing import Any, Dict, Optional, Set, Tuple


class CountingBloomFilter:
    """A thread-safe counting Bloom filter for efficient set membership testing and removal."""

    def __init__(self, capacity: int = 10000, error_rate: float = 0.01):
        self.capacity = capacity
        self.error_rate = error_rate
        
        # Optimal size m = - (n * ln(p)) / (ln(2)^2)
        self.size = int(- (capacity * math.log(error_rate)) / (math.log(2) ** 2))
        self.size = max(self.size, 64)
        
        # Optimal number of hash functions k = (m / n) * ln(2)
        self.hash_count = max(1, int((self.size / capacity) * math.log(2)))
        
        self.table = [0] * self.size
        self._lock = asyncio.Lock()

    def _hashes(self, item: str) -> list[int]:
        # Use double hashing technique based on MD5 and SHA256
        h1 = int(hashlib.md5(item.encode('utf-8')).hexdigest(), 16)
        h2 = int(hashlib.sha256(item.encode('utf-8')).hexdigest(), 16)
        
        return [(h1 + i * h2) % self.size for i in range(self.hash_count)]

    async def add(self, item: str) -> None:
        async with self._lock:
            for h in self._hashes(item):
                self.table[h] += 1

    async def remove(self, item: str) -> None:
        async with self._lock:
            for h in self._hashes(item):
                if self.table[h] > 0:
                    self.table[h] -= 1

    async def __contains__(self, item: str) -> bool:
        async with self._lock:
            for h in self._hashes(item):
                if self.table[h] == 0:
                    return False
            return True


class BoundedLRUGossipRingBuffer:
    """High-performance, memory-bounded LRU message ring-buffer with Bloom filter deduplication."""

    def __init__(self, max_capacity: int = 1000, bloom_capacity: int = 10000, bloom_error_rate: float = 0.01):
        self.max_capacity = max_capacity
        self._cache: Dict[str, Any] = {}
        self._order: list[str] = []
        self._bloom = CountingBloomFilter(capacity=bloom_capacity, error_rate=bloom_error_rate)
        self._lock = asyncio.Lock()

    async def add(self, message_id: str, message: Any) -> Optional[Any]:
        """Adds a message to the ring buffer. Evicts oldest item if capacity is exceeded.
        Returns the evicted message or None.
        """
        evicted_item = None
        async with self._lock:
            if message_id in self._cache:
                # Update LRU order
                self._order.remove(message_id)
                self._order.append(message_id)
                self._cache[message_id] = message
                return None

            if len(self._cache) >= self.max_capacity:
                oldest_id = self._order.pop(0)
                evicted_item = self._cache.pop(oldest_id, None)
                if oldest_id:
                    await self._bloom.remove(oldest_id)

            self._cache[message_id] = message
            self._order.append(message_id)
            await self._bloom.add(message_id)
            return evicted_item

    async def contains(self, message_id: str) -> bool:
        """O(1) check using the counting Bloom filter combined with precise lookup."""
        if message_id not in self._bloom:
            return False
        async with self._lock:
            return message_id in self._cache

    async def get(self, message_id: str) -> Optional[Any]:
        async with self._lock:
            if message_id in self._cache:
                self._order.remove(message_id)
                self._order.append(message_id)
                return self._cache[message_id]
            return None

    async def __len__(self) -> int:
        async with self._lock:
            return len(self._cache)
