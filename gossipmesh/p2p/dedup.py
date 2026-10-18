import math
import hashlib
import threading
from typing import Set

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
        self.lock = threading.Lock()
        self.count = 0

    def _hashes(self, item: str):
        encoded = item.encode('utf-8')
        h1 = int(hashlib.sha256(encoded).hexdigest(), 16)
        h2 = int(hashlib.md5(encoded).hexdigest(), 16)
        for i in range(self.num_hashes):
            yield (h1 + i * h2) % self.size

    def add(self, item: str) -> None:
        with self.lock:
            if self.count >= self.capacity:
                self.clear()
            
            for bit_index in self._hashes(item):
                byte_idx = bit_index // 8
                bit_offset = bit_index % 8
                self.bit_array[byte_idx] |= (1 << bit_offset)
            self.count += 1

    def __contains__(self, item: str) -> bool:
        with self.lock:
            for bit_index in self._hashes(item):
                byte_idx = bit_index // 8
                bit_offset = bit_index % 8
                if not (self.bit_array[byte_idx] & (1 << bit_offset)):
                    return False
            return True

    def clear(self) -> None:
        for i in range(len(self.bit_array)):
            self.bit_array[i] = 0
        self.count = 0

    def memory_usage_bytes(self) -> int:
        return len(self.bit_array)


class GossipTransport:
    """Gossip transport layer wrapper providing integrated message deduplication."""

    def __init__(self, capacity: int = 1000, error_rate: float = 0.01):
        self.bloom_filter = CompressedBloomFilter(capacity=capacity, error_rate=error_rate)

    def should_process_message(self, message_id: str) -> bool:
        if message_id in self.bloom_filter:
            return False
        self.bloom_filter.add(message_id)
        return True
