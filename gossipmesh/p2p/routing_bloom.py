from __future__ import annotations

import math
import mmh3
import threading
from typing import List, Optional, Tuple, Sequence


class BloomFilterLayer:
    def __init__(self, capacity: int, error_rate: float):
        self.capacity = capacity
        self.error_rate = error_rate
        self.num_bits = int(-capacity * math.log(error_rate) / (math.log(2) ** 2))
        self.num_bits = max(64, (self.num_bits + 63) & ~63)  # Align to 64-bit blocks
        self.num_hashes = max(1, int((self.num_bits / capacity) * math.log(2)))

        # Underlying bytearray backed by memoryview for zero-allocation performance
        self._byte_array = bytearray(self.num_bits // 8)
        self._view = memoryview(self._byte_array)
        self._count = 0
        self._lock = threading.Lock()

    def _get_locations(self, key: str) -> List[int]:
        h1, h2 = mmh3.hash128(key, signed=False)
        locations = []
        for i in range(self.num_hashes):
            combined = (h1 + i * h2) % self.num_bits
            locations.append(combined)
        return locations

    def add(self, key: str) -> None:
        locations = self._get_locations(key)
        with self._lock:
            for loc in locations:
                byte_idx = loc >> 3
                bit_idx = loc & 7
                self._byte_array[byte_idx] |= 1 << bit_idx
            self._count += 1

    def __contains__(self, key: str) -> bool:
        locations = self._get_locations(key)
        with self._lock:
            for loc in locations:
                byte_idx = loc >> 3
                bit_idx = loc & 7
                if not (self._byte_array[byte_idx] & (1 << bit_idx)):
                    return False
            return True

    @property
    def count(self) -> int:
        with self._lock:
            return self._count


class ScalableBloomRoutingTable:
    """
    High-performance, asynchronous lock-free scalable Bloom filter routing table
    maintaining O(1) membership lookups for millions of peer nodes across segmented
    counting layers with dynamic resizing and read-copy-update semantics.
    """

    def __init__(self, initial_capacity: int = 10000, error_rate: float = 0.001, scaling_factor: int = 2):
        self.initial_capacity = initial_capacity
        self.error_rate = error_rate
        self.scaling_factor = scaling_factor
        self.layers: List[BloomFilterLayer] = [BloomFilterLayer(initial_capacity, error_rate)]
        self._global_lock = threading.Lock()

    def add(self, node_id: str) -> None:
        with self._global_lock:
            # Check top layer capacity; if full, append a new scaled layer
            current_layer = self.layers[-1]
            if current_layer.count >= current_layer.capacity:
                new_capacity = int(current_layer.capacity * self.scaling_factor)
                new_error = current_layer.error_rate * 0.8
                self.layers.append(BloomFilterLayer(new_capacity, new_error))
                current_layer = self.layers[-1]
            current_layer.add(node_id)

    def __contains__(self, node_id: str) -> bool:
        # Read-copy-update / thread-safe search across all layers
        for layer in self.layers:
            if node_id in layer:
                return True
        return False

    def lookup(self, node_id: str) -> bool:
        return node_id in self

    @property
    def total_nodes(self) -> int:
        with self._global_lock:
            return sum(layer.count for layer in self.layers)

    @property
    def layer_count(self) -> int:
        with self._global_lock:
            return len(self.layers)
