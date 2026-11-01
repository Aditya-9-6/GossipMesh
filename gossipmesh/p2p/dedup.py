from __future__ import annotations

import math
import zlib
import threading
from typing import Set, Optional, Dict, Any


class CountingBloomFilter:
    """
    Thread-safe counting Bloom filter supporting item additions and removals.
    """

    def __init__(self, capacity: int = 1000, error_rate: float = 0.01) -> None:
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
    """
    Bounded LRU ring buffer for gossip messages with integrated Bloom filter deduplication.
    """

    def __init__(self, max_capacity: int = 1000, bloom_capacity: int = 10000) -> None:
        self.max_capacity = max_capacity
        self._buffer: Dict[str, Any] = {}
        self._order: list[str] = []
        self._bloom = CountingBloomFilter(capacity=bloom_capacity)
        self._lock = threading.Lock()

    async def add(self, message_id: str, payload: Any) -> Optional[Any]:
        with self._lock:
            evicted_payload = None
            if message_id in self._buffer:
                self._order.remove(message_id)
            elif len(self._buffer) >= self.max_capacity:
                oldest_id = self._order.pop(0)
                evicted_payload = self._buffer.pop(oldest_id)

            self._buffer[message_id] = payload
            self._order.append(message_id)
            await self._bloom.add(message_id)
            return evicted_payload

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
    """
    Thread-safe sliding-window compressed Bloom filter for message ID deduplication.
    """

    def __init__(self, capacity: int = 10000, error_rate: float = 0.01) -> None:
        self.capacity = capacity
        self.error_rate = error_rate
        self._bits_size = int(-(capacity * math.log(error_rate)) / (math.log(2) ** 2))
        self._num_hashes = max(1, int((self._bits_size / capacity) * math.log(2)))
        max_bytes = 65536
        if (self._bits_size + 7) // 8 > max_bytes:
            self._bits_size = max_bytes * 8
        self._bit_array = bytearray((self._bits_size + 7) // 8)
        self._lock = threading.Lock()
        self._count = 0

    def _hashes(self, item: str) -> list[int]:
        encoded = item.encode("utf-8")
        h1 = zlib.crc32(encoded)
        h2 = zlib.adler32(encoded)
        return [(h1 + i * h2) % self._bits_size for i in range(self._num_hashes)]

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
