<<<<<<< HEAD
import time
import threading
from collections import OrderedDict
from typing import Optional, Any

class LRUDigestCache:
    """High-performance, memory-bounded Least Recently Used (LRU) cache
    with time-to-live (TTL) expiry for tracking seen gossip message IDs."""
    
    def __init__(self, max_size: int = 10000, default_ttl: float = 86400.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()
        self._last_evict_time = 0.0

    def _evict_expired(self, now: float):
        # Amortize full scans or only scan if enough time has elapsed or cache is large
        if now - self._last_evict_time < 0.5 and len(self._cache) < self.max_size:
            return
        self._last_evict_time = now
        keys_to_delete = []
        for k, expiry in self._cache.items():
            if expiry <= now:
                keys_to_delete.append(k)
            else:
                break
        for k in keys_to_delete:
            self._cache.pop(k, None)

    def add(self, message_id: str, ttl: Optional[float] = None) -> None:
        now = time.time()
        expiry = now + (ttl if ttl is not None else self.default_ttl)
        with self._lock:
            self._evict_expired(now)
            if message_id in self._cache:
                self._cache.move_to_end(message_id)
            self._cache[message_id] = expiry
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def contains(self, message_id: str) -> bool:
        now = time.time()
        with self._lock:
            expiry = self._cache.get(message_id)
            if expiry is None:
                return False
            if expiry <= now:
                self._cache.pop(message_id, None)
                return False
            self._cache.move_to_end(message_id)
            return True

    def __contains__(self, message_id: str) -> bool:
        return self.contains(message_id)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        now = time.time()
        with self._lock:
            self._evict_expired(now)
            return len(self._cache)
=======
import math
import hashlib
import base64
import threading
from typing import Set, List, Dict, Any, Optional

class BloomFilterDigest:
    """Space-efficient dynamic Bloom filter digest for P2P anti-entropy state reconciliation."""
    
    def __init__(self, capacity: int = 1000, error_rate: float = 0.01) -> None:
        self.capacity = max(1, capacity)
        self.error_rate = min(max(0.0001, error_rate), 0.5)
        self._size = 0
        self._bit_array_size = int(-self.capacity * math.log(self.error_rate) / (math.log(2) ** 2))
        self._bit_array_size = max(64, self._bit_array_size)
        self._num_hashes = int(max(1, round((self._bit_array_size / self.capacity) * math.log(2))))
        self._bits = [0] * ((self._bit_array_size + 63) // 64)
        self._lock = threading.Lock()

    @property
    def size(self) -> int:
        with self._lock:
            return self._size

    @property
    def element_count(self) -> int:
        with self._lock:
            return self._size

    @property
    def hash_count(self) -> int:
        return self._num_hashes

    def _get_hashes(self, item: str) -> List[int]:
        digest1 = int(hashlib.sha256(item.encode('utf-8')).hexdigest(), 16)
        digest2 = int(hashlib.md5(item.encode('utf-8')).hexdigest(), 16)
        return [(digest1 + i * digest2) % self._bit_array_size for i in range(self._num_hashes)]

    def add(self, item: str) -> None:
        with self._lock:
            for h in self._get_hashes(item):
                idx = h // 64
                bit = h % 64
                if not (self._bits[idx] & (1 << bit)):
                    self._bits[idx] |= (1 << bit)
                    self._size += 1

    def __contains__(self, item: str) -> bool:
        return self.contains(item)

    def contains(self, item: str) -> bool:
        with self._lock:
            for h in self._get_hashes(item):
                idx = h // 64
                bit = h % 64
                if not (self._bits[idx] & (1 << bit)):
                    return False
            return True

    def serialize(self) -> Dict[str, Any]:
        with self._lock:
            bit_bytes = bytearray()
            for word in self._bits:
                bit_bytes.extend(word.to_bytes(8, byteorder='big', signed=False))
            encoded = base64.b64encode(bytes(bit_bytes)).decode('utf-8')
            return {
                "capacity": self.capacity,
                "error_rate": self.error_rate,
                "size": self._size,
                "element_count": self._size,
                "bit_array_size": self._bit_array_size,
                "num_hashes": self._num_hashes,
                "hash_count": self._num_hashes,
                "bits": encoded,
            }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "BloomFilterDigest":
        instance = cls(capacity=data["capacity"], error_rate=data["error_rate"])
        size_val = data.get("size", data.get("element_count", 0))
        instance._size = size_val
        instance._bit_array_size = data.get("bit_array_size", instance._bit_array_size)
        instance._num_hashes = data.get("num_hashes", data.get("hash_count", instance._num_hashes))
        decoded = base64.b64decode(data["bits"].encode('utf-8'))
        instance._bits = [int.from_bytes(decoded[i:i+8], byteorder='big', signed=False) for i in range(0, len(decoded), 8)]
        return instance
>>>>>>> origin/main
