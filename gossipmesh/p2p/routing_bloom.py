"""
Scalable Bloom Routing Table for P2P message forwarding.
"""

import math
import zlib
import threading
from typing import List


class BloomFilterLayer:
    def __init__(self, capacity: int = 100, error_rate: float = 0.01):
        self.capacity = capacity
        self.error_rate = error_rate
        self._bits_size = int(-(capacity * math.log(error_rate)) / (math.log(2) ** 2))
        self._bit_array = bytearray((self._bits_size + 7) // 8)
        self._count = 0
        self._lock = threading.Lock()

    def _hashes(self, item: str) -> List[int]:
        encoded = item.encode("utf-8")
        h1 = zlib.crc32(encoded)
        h2 = zlib.adler32(encoded)
        return [(h1 + i * h2) % self._bits_size for i in range(2)]

    def add(self, item: str) -> None:
        with self._lock:
            for idx in self._hashes(item):
                self._bit_array[idx // 8] |= 1 << (idx % 8)
            self._count += 1

    def __contains__(self, item: str) -> bool:
        with self._lock:
            for idx in self._hashes(item):
                if not (self._bit_array[idx // 8] & (1 << (idx % 8))):
                    return False
            return True


class ScalableBloomRoutingTable:
    def __init__(self, initial_capacity: int = 100, error_rate: float = 0.01, scaling_factor: int = 2):
        self.initial_capacity = initial_capacity
        self.error_rate = error_rate
        self.scaling_factor = scaling_factor
        self.layers: List[BloomFilterLayer] = [BloomFilterLayer(initial_capacity, error_rate)]
        self._total_nodes = 0
        self._lock = threading.Lock()

    def add(self, item: str) -> None:
        with self._lock:
            current_layer = self.layers[-1]
            if current_layer._count >= current_layer.capacity:
                new_cap = current_layer.capacity * self.scaling_factor
                new_error = current_layer.error_rate * 0.5
                current_layer = BloomFilterLayer(new_cap, new_error)
                self.layers.append(current_layer)
            current_layer.add(item)
            self._total_nodes += 1

    def __contains__(self, item: str) -> bool:
        with self._lock:
            for layer in reversed(self.layers):
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
            return self._total_nodes
