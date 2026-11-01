"""
Scalable Bloom Routing Table for P2P network topologies.
"""

from __future__ import annotations

import math
import threading
from typing import List, Optional


class BloomFilterLayer:
    def __init__(self, capacity: int = 1000, error_rate: float = 0.01):
        self.capacity = capacity
        self.error_rate = error_rate
        self._bits = 1024
        self._bit_array = bytearray(self._bits // 8)
        self._count = 0

    def _hash(self, item: str) -> int:
        return abs(hash(item)) % self._bits

    def add(self, item: str) -> None:
        idx = self._hash(item)
        byte_idx = idx // 8
        bit_idx = idx % 8
        self._bit_array[byte_idx] |= 1 << bit_idx
        self._count += 1

    def __contains__(self, item: str) -> bool:
        idx = self._hash(item)
        byte_idx = idx // 8
        bit_idx = idx % 8
        return bool(self._bit_array[byte_idx] & (1 << bit_idx))


class ScalableBloomRoutingTable:
    def __init__(self, initial_capacity: int = 100, error_rate: float = 0.01, scaling_factor: int = 2):
        self.initial_capacity = initial_capacity
        self.error_rate = error_rate
        self.scaling_factor = scaling_factor
        self.layers: List[BloomFilterLayer] = [BloomFilterLayer(initial_capacity, error_rate)]
        self._lock = threading.Lock()
        self._total_nodes = 0

    def add(self, node_id: str) -> None:
        with self._lock:
            current_layer = self.layers[-1]
            if current_layer._count >= current_layer.capacity:
                new_capacity = current_layer.capacity * self.scaling_factor
                current_layer = BloomFilterLayer(new_capacity, self.error_rate)
                self.layers.append(current_layer)
            current_layer.add(node_id)
            self._total_nodes += 1

    def __contains__(self, node_id: str) -> bool:
        with self._lock:
            for layer in reversed(self.layers):
                if node_id in layer:
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
