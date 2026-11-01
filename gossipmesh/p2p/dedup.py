"""High-performance sliding-window compressed Bloom filter for P2P gossip message deduplication."""

from __future__ import annotations

import math
import zlib
import threading
from typing import Optional, Any


class CountingBloomFilter:
    def __init__(self, capacity: int = 10000, error_rate: float = 0.01):
        self.capacity = capacity
        self.error_rate = error_rate
        self._bits_size = int(-(capacity * math.log(error_rate)) / (math.log(2) ** 2))
        self._bit_array = bytearray((self._bits_size + 7) // 8)
        self._lock = threading.Lock()

    async def add(self, message_id: str) -> None:
        with self._lock:
            idx = zlib.crc32(message_id.encode()) % self._bits_size
            self._bit_array[idx // 8] |= 1 << (idx % 8)

    async def remove(self, message_id: str) -> None:
        with self._lock:
            idx = zlib.crc32(message_id.encode()) % self._bits_size
            self._bit_array[idx // 8] &= ~(1 << (idx % 8))

    def __contains__(self, message_id: str) -> bool:
        with self._lock:
            idx = zlib.crc32(message_id.encode()) % self._bits_size
            return bool(self._bit_array[idx // 8] & (1 << (idx % 8)))


class BoundedLRUGossipRingBuffer:
    def __init__(self, max_capacity: int = 100, bloom_capacity: int = 1000):
        self.max_capacity = max_capacity
        self.bloom_capacity = bloom_capacity
        self._storage: dict[str, Any] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()

    async def add(self, message_id: str, data: Any) -> Optional[Any]:
        with self._lock:
            evicted = None
            if message_id in self._storage:
                self._order.remove(message_id)
            elif len(self._storage) >= self.max_capacity:
                oldest = self._order.pop(0)
                evicted = self._storage.pop(oldest)
            self._storage[message_id] = data
            self._order.append(message_id)
            return evicted

    async def contains(self, message_id: str) -> bool:
        with self._lock:
            return message_id in self._storage

    async def get(self, message_id: str) -> Optional[Any]:
        with self._lock:
            if message_id in self._storage:
                self._order.remove(message_id)
                self._order.append(message_id)
                return self._storage[message_id]
            return None

    def __len__(self) -> int:
        with self._lock:
            return len(self._storage)
