import threading
import math
from typing import List, Optional


class BloomFilterLayer:
    def __init__(self, capacity: int = 1000, error_rate: float = 0.01):
        self.capacity = capacity
        self.error_rate = error_rate
        self._bits_size = int(-(capacity * math.log(error_rate)) / (math.log(2) ** 2))
        self._num_hashes = max(1, int((self._bits_size / capacity) * math.log(2)))
        self._bit_array = bytearray((self._bits_size + 7) // 8)
        self._lock = threading.Lock()

    def _hashes(self, item: str) -> List[int]:
        h1 = hash(item) & 0xFFFFFFFF
        h2 = (hash(item) >> 32) & 0xFFFFFFFF
        return [(h1 + i * h2) % self._bits_size for i in range(self._num_hashes)]

    def add(self, item: str) -> None:
        with self._lock:
            for idx in self._hashes(item):
                self._bit_array[idx // 8] |= 1 << (idx % 8)

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

    def add(self, node_id: str) -> None:
        with self._lock:
            current_layer = self.layers[-1]
            if self._total_nodes >= current_layer.capacity:
                new_capacity = current_layer.capacity * self.scaling_factor
                current_layer = BloomFilterLayer(new_capacity, self.error_rate)
                self.layers.append(current_layer)
            current_layer.add(node_id)
            self._total_nodes += 1

    @property
    def layer_count(self) -> int:
        with self._lock:
            return len(self.layers)

    @property
    def total_nodes(self) -> int:
        with self._lock:
            return self._total_nodes

    def __contains__(self, node_id: str) -> bool:
        with self._lock:
            for layer in self.layers:
                if node_id in layer:
                    return True
            return False
