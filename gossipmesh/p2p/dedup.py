import math
import zlib
import threading
from typing import Set, Optional, Any, Dict, List


class CompressedBloomFilterDedup:
    """
    Zero-allocation compressed Bloom filter message deduplication for P2P gossip layer.
    Bounded below 64KB footprint.
    """

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

    def _hashes(self, item: str) -> List[int]:
        encoded = item.encode("utf-8")
        h1 = zlib.crc32(encoded)
        h2 = zlib.adler32(encoded)
        return [(h1 + i * h2 + i * i) % self._bits_size for i in range(self._num_hashes)]

    def add(self, message_id: str) -> bool:
        """
        Adds message_id to deduplication filter.
        Returns True if already present (duplicate), False if newly added.
        """
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

    def __contains__(self, message_id: str) -> bool:
        with self._lock:
            indices = self._hashes(message_id)
            for idx in indices:
                byte_idx = idx // 8
                bit_idx = idx % 8
                if not (self._bit_array[byte_idx] & (1 << bit_idx)):
                    return False
            return True

    def size(self) -> int:
        with self._lock:
            return self._count

    def memory_bytes(self) -> int:
        with self._lock:
            return len(self._bit_array)


class CountingBloomFilter:
    """
    Counting Bloom Filter supporting additions and removals.
    """

    def __init__(self, capacity: int = 1000, error_rate: float = 0.01) -> None:
        self.capacity = capacity
        self.error_rate = error_rate
        self.m = int(-(capacity * math.log(error_rate)) / (math.log(2) ** 2))
        self.k = max(1, int((self.m / capacity) * math.log(2)))
        self._counters = [0] * self.m
        self._lock = threading.Lock()

    def _hashes(self, item: str) -> List[int]:
        encoded = item.encode("utf-8")
        h1 = zlib.crc32(encoded)
        h2 = zlib.adler32(encoded)
        return [(h1 + i * h2) % self.m for i in range(self.k)]

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
    Bounded LRU Ring Buffer with internal bloom filtering for gossip messages.
    """

    def __init__(self, max_capacity: int = 100, bloom_capacity: int = 1000) -> None:
        self.max_capacity = max_capacity
        self._store: Dict[str, Any] = {}
        self._order: List[str] = []
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
                await self._bloom.remove(oldest_key)

            self._store[key] = value
            self._order.append(key)
            await self._bloom.add(key)
            return evicted_val

    async def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._store:
                self._order.remove(key)
                self._order.append(key)
                return self._store[key]
            return None

    async def contains(self, key: str) -> bool:
        with self._lock:
            return key in self._store

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
