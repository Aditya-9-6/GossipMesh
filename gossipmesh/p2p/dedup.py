import math
import zlib
import threading
from typing import Dict, Any, Optional


class CountingBloomFilter:
    def __init__(self, capacity: int = 100, error_rate: float = 0.01):
        self.capacity = capacity
        self.error_rate = error_rate
        self._bits_size = int(-(capacity * math.log(error_rate)) / (math.log(2) ** 2))
        self._num_hashes = max(1, int((self._bits_size / capacity) * math.log(2)))
        self._counters = [0] * self._bits_size
        self._lock = threading.Lock()

    def _hashes(self, item: str) -> list[int]:
        encoded = item.encode("utf-8")
        h1 = zlib.crc32(encoded)
        h2 = zlib.adler32(encoded)
        return [(h1 + i * h2) % self._bits_size for i in range(self._num_hashes)]

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
    def __init__(self, max_capacity: int = 1000, bloom_capacity: int = 10000):
        self.max_capacity = max_capacity
        self.bloom = CountingBloomFilter(capacity=bloom_capacity)
        self._storage: Dict[str, Any] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()

    async def add(self, message_id: str, payload: Any) -> Optional[Any]:
        with self._lock:
            evicted_payload = None
            if message_id in self._storage:
                self._order.remove(message_id)
            elif len(self._storage) >= self.max_capacity:
                oldest_id = self._order.pop(0)
                evicted_payload = self._storage.pop(oldest_id)
                await self.bloom.remove(oldest_id)

            self._storage[message_id] = payload
            self._order.append(message_id)
            await self.bloom.add(message_id)
            return evicted_payload

    async def get(self, message_id: str) -> Optional[Any]:
        with self._lock:
            if message_id in self._storage:
                self._order.remove(message_id)
                self._order.append(message_id)
                return self._storage[message_id]
            return None

    async def contains(self, message_id: str) -> bool:
        with self._lock:
            return message_id in self._storage

    def __len__(self) -> int:
        with self._lock:
            return len(self._storage)
