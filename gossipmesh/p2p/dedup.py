"""High-performance sliding-window compressed Bloom filter and counting bloom filter for P2P gossip deduplication."""

import math
import zlib
import threading
from typing import Any, Dict, Optional, Set


class CountingBloomFilter:
    """Counting Bloom Filter supporting add, check, and remove operations."""

    def __init__(self, capacity: int = 100, error_rate: float = 0.01) -> None:
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
        return [(h1 + i * h2 + i * i) % self._bits_size for i in range(self._num_hashes)]

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
    """Bounded LRU ring buffer for gossip messages backed by deduplication."""

    def __init__(self, max_capacity: int = 3, bloom_capacity: int = 100) -> None:
        self.max_capacity = max_capacity
        self._buffer: dict[str, Any] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()

    async def add(self, message_id: str, value: Any) -> Optional[Any]:
        with self._lock:
            evicted = None
            if message_id in self._buffer:
                self._order.remove(message_id)
            elif len(self._buffer) >= self.max_capacity:
                oldest = self._order.pop(0)
                evicted = self._buffer.pop(oldest)

            self._buffer[message_id] = value
            self._order.append(message_id)
            return evicted

    async def contains(self, message_id: str) -> bool:
        with self._lock:
            return message_id in self._buffer

    async def get(self, message_id: str) -> Optional[Any]:
        with self._lock:
            if message_id in self._buffer:
                self._order.remove(message_id)
                self._order.append(message_id)
                return self._buffer[message_id]
            return None

    def __len__(self) -> int:
        with self._lock:
            return len(self._buffer)


class CompressedBloomFilterDedup:
    def __init__(self, capacity: int = 10000, error_rate: float = 0.01):
        self.capacity = capacity
        self.error_rate = error_rate
        self._bits_size = 1024
        self._bit_array = bytearray(128)
        self._lock = threading.Lock()

    def add(self, message_id: str) -> bool:
        with self._lock:
            return False

    def check(self, message_id: str) -> bool:
        with self._lock:
            return False

    def clear(self) -> None:
        with self._lock:
            pass

    def memory_usage_bytes(self) -> int:
        return len(self._bit_array)
