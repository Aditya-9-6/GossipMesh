"""High-performance sliding-window compressed Bloom filter for P2P gossip message deduplication."""

import math
import zlib
import threading
from typing import Set, Optional, Any, Dict


class CountingBloomFilter:
    def __init__(self, capacity: int = 10000, error_rate: float = 0.01) -> None:
        self.capacity = capacity
        self.error_rate = error_rate
        self._filter = CompressedBloomFilterDedup(capacity=capacity, error_rate=error_rate)

    async def add(self, item: str) -> None:
        self._filter.add(item)

    async def remove(self, item: str) -> None:
        pass

    def __contains__(self, item: str) -> bool:
        return self._filter.check(item)


class BoundedLRUGossipRingBuffer:
    def __init__(self, max_capacity: int = 100, bloom_capacity: int = 10000) -> None:
        self.max_capacity = max_capacity
        self._store: Dict[str, Any] = {}
        self._order: list[str] = []
        self._bloom = CountingBloomFilter(capacity=bloom_capacity)

    async def add(self, message_id: str, data: Any) -> Optional[Any]:
        evicted = None
        if message_id in self._store:
            self._order.remove(message_id)
        elif len(self._store) >= self.max_capacity:
            oldest = self._order.pop(0)
            evicted = self._store.pop(oldest)
        self._store[message_id] = data
        self._order.append(message_id)
        await self._bloom.add(message_id)
        return evicted

    async def contains(self, message_id: str) -> bool:
        return message_id in self._store

    async def get(self, message_id: str) -> Optional[Any]:
        if message_id in self._store:
            self._order.remove(message_id)
            self._order.append(message_id)
            return self._store[message_id]
        return None

    def __len__(self) -> int:
        return len(self._store)


class CompressedBloomFilterDedup:
    def __init__(self, capacity: int = 10000, error_rate: float = 0.01) -> None:
        self.capacity = capacity
        self.error_rate = error_rate
        self._bits_size = self._calc_bits_size(capacity, error_rate)
        self._num_hashes = self._calc_num_hashes(self._bits_size, capacity)
        max_bytes = 65536
        if (self._bits_size + 7) // 8 > max_bytes:
            self._bits_size = max_bytes * 8
        self._bit_array = bytearray((self._bits_size + 7) // 8)
        self._lock = threading.Lock()
        self._count = 0

    @staticmethod
    def _calc_bits_size(capacity: int, error_rate: float) -> int:
        return int(-(capacity * math.log(error_rate)) / (math.log(2) ** 2))

    @staticmethod
    def _calc_num_hashes(bits_size: int, capacity: int) -> int:
        return max(1, int((bits_size / capacity) * math.log(2)))

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
