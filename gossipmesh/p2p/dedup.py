import math
import threading
from typing import Generator

class CompressedBloomFilter:
    """Compressed Bloom Filter for P2P message deduplication using pure Python hash functions."""

    def __init__(self, capacity: int = 1000, error_rate: float = 0.01):
        self.capacity = capacity
        self.error_rate = error_rate
        
        # Optimal bit array size m = - (n * ln(p)) / (ln(2)^2)
        self.size = int(- (capacity * math.log(error_rate)) / (math.log(2) ** 2))
        self.size = max(self.size, 64)
        
        # Optimal number of hash functions k = (m / n) * ln(2)
        self.num_hashes = max(1, int((self.size / capacity) * math.log(2)))
        
        self.bit_array = bytearray(math.ceil(self.size / 8))
        self.lock = threading.RLock()
        self.count = 0

    def _hashes(self, item: str) -> Generator[int, None, None]:
        # Use lightweight hash or fast integer mixing instead of heavy string conversions
        val = hash(item)
        h1 = val & 0xFFFFFFFF
        h2 = (val >> 32) & 0xFFFFFFFF
        if h2 == 0:
            h2 = 0x9e3779b9
        for i in range(self.num_hashes):
            yield (h1 + i * h2) % self.size

    def add(self, item: str) -> None:
        with self.lock:
            if self.count >= self.capacity:
                self.clear_unlocked()
            
            for bit_index in self._hashes(item):
                byte_idx = bit_index // 8
                bit_offset = bit_index % 8
                self.bit_array[byte_idx] |= (1 << bit_offset)
            self.count += 1

    def check_and_add(self, item: str) -> bool:
        """Atomically checks if an item is in the filter; if not, adds it and returns True. Prevents TOCTOU race."""
        with self.lock:
            # Check membership first
            present = True
            indexes = list(self._hashes(item))
            for bit_index in indexes:
                byte_idx = bit_index // 8
                bit_offset = bit_index % 8
                if not (self.bit_array[byte_idx] & (1 << bit_offset)):
                    present = False
                    break
            
            if present:
                return False
            
            if self.count >= self.capacity:
                self.clear_unlocked()
                # Recalculate indexes after clear if needed, or proceed
                indexes = list(self._hashes(item))

            for bit_index in indexes:
                byte_idx = bit_index // 8
                bit_offset = bit_index % 8
                self.bit_array[byte_idx] |= (1 << bit_offset)
            self.count += 1
            return True

    def __contains__(self, item: str) -> bool:
        with self.lock:
            for bit_index in self._hashes(item):
                byte_idx = bit_index // 8
                bit_offset = bit_index % 8
                if not (self.bit_array[byte_idx] & (1 << bit_offset)):
                    return False
            return True

    def clear_unlocked(self) -> None:
        for i in range(len(self.bit_array)):
            self.bit_array[i] = 0
        self.count = 0

    def clear(self) -> None:
        with self.lock:
            self.clear_unlocked()

    def memory_usage_bytes(self) -> int:
        with self.lock:
            return len(self.bit_array)
