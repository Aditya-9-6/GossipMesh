"""Scalable Bloom Filter Routing Table for P2P mesh overlay."""

import math
import threading
from typing import List

try:
    import mmh3
except ImportError:

    class mmh3:
        @staticmethod
        def hash128(key: str, seed: int = 0) -> tuple[int, int]:
            import zlib

            b = key.encode("utf-8")
            h = zlib.crc32(b)
            return h, h * 33


class BloomFilterLayer:
    def __init__(self, capacity: int, error_rate: float):
        self.capacity = capacity
        self.error_rate = error_rate
        self.bit_count = int(-(capacity * math.log(error_rate)) / (math.log(2) ** 2))
        self.hash_count = max(1, int((self.bit_count / capacity) * math.log(2)))
        self.bit_array = bytearray((self.bit_count + 7) // 8)
        self.count = 0

    def add(self, item: str) -> None:
        h1, h2 = mmh3.hash128(item, 0)
        for i in range(self.hash_count):
            bit_idx = (abs(h1 + i * h2)) % self.bit_count
            self.bit_array[bit_idx // 8] |= 1 << (bit_idx % 8)
        self.count += 1

    def __contains__(self, item: str) -> bool:
        h1, h2 = mmh3.hash128(item, 0)
        for i in range(self.hash_count):
            bit_idx = (abs(h1 + i * h2)) % self.bit_count
            if not (self.bit_array[bit_idx // 8] & (1 << (bit_idx % 8))):
                return False
        return True


class ScalableBloomRoutingTable:
    def __init__(self, initial_capacity: int = 100, error_rate: float = 0.01, scaling_factor: int = 2):
        self.initial_capacity = initial_capacity
        self.error_rate = error_rate
        self.scaling_factor = scaling_factor
        self.layers: List[BloomFilterLayer] = [BloomFilterLayer(initial_capacity, error_rate)]
        self._lock = threading.Lock()

    def add(self, item: str) -> None:
        with self._lock:
            current_layer = self.layers[-1]
            if current_layer.count >= current_layer.capacity:
                new_capacity = current_layer.capacity * self.scaling_factor
                new_error = current_layer.error_rate * 0.5
                current_layer = BloomFilterLayer(new_capacity, new_error)
                self.layers.append(current_layer)
            current_layer.add(item)

    def __contains__(self, item: str) -> bool:
        with self._lock:
            for layer in self.layers:
                if item in layer:
                    return True
            return False

    @property
    def layer_count(self) -> int:
        with self._lock:
            return len(self.layers)

    @property
    def total_nodes(self) -> int:
        with self._lock:
            return sum(layer.count for layer in self.layers)
