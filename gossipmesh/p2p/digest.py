import math
import hashlib
import threading
from typing import List, Iterable, Union

class BloomFilterDigest:
    """Memory-efficient, thread-safe Bloom filter for P2P anti-entropy digest exchange."""

    def __init__(self, capacity: int = 100000, error_rate: float = 0.01):
        self.capacity = max(1, capacity)
        self.error_rate = min(max(error_rate, 0.0001), 0.5)
        
        # Compute optimal bit array size (m) and hash count (k)
        self.size = int(- (self.capacity * math.log(self.error_rate)) / (math.log(2) ** 2))
        self.hash_count = max(1, int((self.size / self.capacity) * math.log(2)))
        
        self.bit_array = 0
        self._lock = threading.Lock()

    def _hashes(self, item: Union[str, bytes]) -> Iterable[int]:
        if isinstance(item, str):
            item_bytes = item.encode('utf-8')
        else:
            item_bytes = item
            
        h1 = int.from_bytes(hashlib.md5(item_bytes).digest()[:8], 'big')
        h2 = int.from_bytes(hashlib.sha256(item_bytes).digest()[:8], 'big')
        
        for i in range(self.hash_count):
            yield (h1 + i * h2) % self.size

    def add(self, item: Union[str, bytes]) -> None:
        """Add an item to the bloom filter."""
        with self._lock:
            mask = 0
            for bit_index in self._hashes(item):
                mask |= (1 << bit_index)
            self.bit_array |= mask

    def __contains__(self, item: Union[str, bytes]) -> bool:
        """Check if an item might be in the set."""
        with self._lock:
            for bit_index in self._hashes(item):
                if not (self.bit_array & (1 << bit_index)):
                    return False
            return True

    def serialize(self) -> dict:
        """Serialize the bloom filter state for digest wire transmission."""
        with self._lock:
            hex_val = format(self.bit_array, 'x')
            return {
                "capacity": self.capacity,
                "error_rate": self.error_rate,
                "size": self.size,
                "hash_count": self.hash_count,
                "bit_array_hex": hex_val
            }

    @classmethod
    def deserialize(cls, data: dict) -> "BloomFilterDigest":
        """Restore a BloomFilterDigest from its serialized dict form."""
        instance = cls(capacity=data["capacity"], error_rate=data["error_rate"])
        instance.size = data["size"]
        instance.hash_count = data["hash_count"]
        instance.bit_array = int(data["bit_array_hex"], 16)
        return instance
