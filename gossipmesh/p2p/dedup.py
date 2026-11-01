"""High-performance sliding-window compressed Bloom filter for P2P gossip message deduplication."""

import math
import zlib
import threading
from typing import Set, Optional, Any


class CountingBloomFilter:
    def __init__(self, capacity: int = 10000, error_rate: float = 0.01) -> None:
        self.capacity = capacity
        self.error_rate = error_rate
        self._bits = [0] * capacity
        self._lock = threading.Lock()

    def __contains__(self, item: str) -> bool:
        with self._lock:
            idx = abs(hash(item)) % self.capacity
            return self._bits[idx] > 0

    async def add(self, item: str) -> None:
        with self._lock:
            idx = abs(hash(item)) % self.capacity
            self._bits[idx] += 1

    async def remove(self, item: str) -> None:
        with self._lock:
            idx = abs(hash(item)) % self.capacity
            if self._bits[idx] > 0:
                self._bits[idx] -= 1


class BoundedLRUGossipRingBuffer:
    def __init__(self, max_capacity: int = 100, bloom_capacity: int = 10000) -> None:
        self.max_capacity = max_capacity
        self._store: dict[str, Any] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    async def add(self, key: str, value: Any) -> Optional[Any]:
        with self._lock:
            evicted = None
            if key in self._store:
                self._order.remove(key)
            elif len(self._store) >= self.max_capacity:
                oldest = self._order.pop(0)
                evicted = self._store.pop(oldest)
            self._store[key] = value
            self._order.append(key)
            return evicted

    async def contains(self, key: str) -> bool:
        with self._lock:
            return key in self._store

    async def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._store:
                self._order.remove(key)
                self._order.append(key)
                return self._store[key]
            return None


class CompressedBloomFilterDedup:
    def __init__(self, capacity: int = 10000, error_rate: float = 0.01) -> None:
        self.capacity = capacity
        self.error_rate = error_rate
        self._bits_size = int(-(capacity * math.log(error_rate)) / (math.log(2) ** 2))
        self._num_hashes = max(1, int((self._bits_size / capacity) * math.log(2)))
        self._bit_array = bytearray((self._bits_size + 7) // 8)
        self._lock = threading.Lock()
        self._count = 0

    def _hashes(self, item: str) -> list[int]:
        encoded = item.encode("utf-8")
        h1 = zlib.crc32(encoded)
        h2 = zlib.adler32(encoded)
        return [(h1 + i * h2 + i * i) % self._bits_size for i in range(self._num_hashes)]

    def add(self, message_id: str) -> bool:
        with self._lock:
            indices = self._hashes(message_id)
            is_present = True
            for idx in indices:
                byte_idx = idx // 8
                bit_idx = idx % 8
                if not (self._bit_array[byte_idx] & (1 << bit_idx)):
                    is_present = False
                    self._bit_array[byte_idx] |= 1 << bit_idx
            if not is_present:
                self._count += 1
            return is_present

    def check(self, message_id: str) -> bool:
        with self._lock:
            indices = self._hashes(message_id)
            for idx in indices:
                byte_idx = idx // 8
                bit_idx = idx % 8
                if not (self._bit_array[byte_idx] & (1 << bit_idx)):
                    return False
            return True

    def clear(self) -> None:
        with self._lock:
            for i in range(len(self._bit_array)):
                self._bit_array[i] = 0
            self._count = 0

    def memory_usage_bytes(self) -> int:
        with self._lock:
            return len(self._bit_array)
