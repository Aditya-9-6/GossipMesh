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
        digest1 = int(hashlib.sha256(item.encode("utf-8")).hexdigest(), 16)
        digest2 = int(hashlib.md5(item.encode("utf-8")).hexdigest(), 16)
        return [(digest1 + i * digest2) % self._bit_array_size for i in range(self._num_hashes)]

    def add(self, item: str) -> None:
        with self._lock:
            for h in self._get_hashes(item):
                idx = h // 64
                bit = h % 64
                if not (self._bits[idx] & (1 << bit)):
                    self._bits[idx] |= 1 << bit
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
                bit_bytes.extend(word.to_bytes(8, byteorder="big", signed=False))
            encoded = base64.b64encode(bytes(bit_bytes)).decode("utf-8")
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
        decoded = base64.b64decode(data["bits"].encode("utf-8"))
        instance._bits = [
            int.from_bytes(decoded[i : i + 8], byteorder="big", signed=False) for i in range(0, len(decoded), 8)
        ]
        return instance


class HyperLogLogDigest:
    """Memory-bounded HyperLogLog probabilistic cardinality estimator digest for GossipMesh state-sync."""

    def __init__(self, precision: int = 12) -> None:
        self.precision = max(4, min(precision, 18))
        self.m = 1 << self.precision
        self._registers = [0] * self.m
        self._lock = threading.Lock()
        
        # Alpha constant determination
        if self.m == 16:
            self._alpha = 0.673
        elif self.m == 32:
            self._alpha = 0.697
        elif self.m == 64:
            self._alpha = 0.709
        else:
            self._alpha = 0.7213 / (1.0 + 1.079 / self.m)

    @property
    def cardinality(self) -> float:
        with self._lock:
            return self._estimate_cardinality()

    def _get_register_and_rank(self, item: str) -> Tuple[int, int]:
        h = int(hashlib.sha256(item.encode("utf-8")).hexdigest(), 16)
        idx = h & (self.m - 1)
        w = h >> self.precision
        # Find position of first set bit starting from least significant bit
        if w == 0:
            rank = 64 - self.precision + 1
        else:
            rank = (w & -w).bit_length()
        return idx, rank

    def add(self, item: str) -> None:
        idx, rank = self._get_register_and_rank(item)
        with self._lock:
            if rank > self._registers[idx]:
                self._registers[idx] = rank

    def __contains__(self, item: str) -> bool:
        return True  # Probabilistic digest supports cardinality estimation, not exact membership

    def _estimate_cardinality(self) -> float:
        raw_sum = sum(2.0 ** (-r) for r in self._registers)
        if raw_sum == 0:
            return 0.0
        estimate = self._alpha * (self.m ** 2) / raw_sum

        # Small range correction (LinearCounting)
        if estimate <= 2.5 * self.m:
            zeros = self._registers.count(0)
            if zeros > 0:
                estimate = self.m * math.log(self.m / zeros)

        # Large range correction
        elif estimate > (1.0 / 30.0) * (2.0 ** 32):
            estimate = -(2.0 ** 32) * math.log(1.0 - estimate / (2.0 ** 32))

        return estimate

    def merge(self, other: "HyperLogLogDigest") -> "HyperLogLogDigest":
        with self._lock:
            with other._lock:
                for i in range(self.m):
                    if other._registers[i] > self._registers[i]:
                        self._registers[i] = other._registers[i]
        return self

    def serialize(self) -> Dict[str, Any]:
        with self._lock:
            reg_bytes = bytearray()
            for r in self._registers:
                reg_bytes.append(r)
            encoded = base64.b64encode(bytes(reg_bytes)).decode("utf-8")
            return {
                "precision": self.precision,
                "m": self.m,
                "registers": encoded,
                "estimated_cardinality": self._estimate_cardinality(),
            }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "HyperLogLogDigest":
        precision = data.get("precision", 12)
        instance = cls(precision=precision)
        decoded = base64.b64decode(data["registers"].encode("utf-8"))
        instance._registers = [int(b) for b in decoded]
        return instance
