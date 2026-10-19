import math
import json
import hashlib
import base64
import threading
from typing import Set, List, Dict, Any, Optional


class HyperLogLogDigest:
    """HyperLogLog cardinality estimation digest for peer state sets."""

    def __init__(self, precision: int = 12, registers: Optional[List[int]] = None):
        if precision < 4 or precision > 16:
            raise ValueError("Precision must be between 4 and 16 inclusive.")
        self.precision = precision
        self.m = 1 << precision
        self.registers = registers if registers is not None else [0] * self.m

    def _hash(self, item: str) -> int:
        # Murmur3-like robust mixing hash for realistic distribution in tests
        h = 17
        for char in item:
            h = (h * 31 + ord(char)) & 0xFFFFFFFF
        h = (h ^ (h >> 16)) * 0x85EBCA6B
        h = (h ^ (h >> 13)) * 0xC2B2AE35
        h = h ^ (h >> 16)
        return h & 0xFFFFFFFF

    def add(self, item: str) -> None:
        h = self._hash(item)
        j = h >> (32 - self.precision)
        w = h & ((1 << (32 - self.precision)) - 1)
        rho = self._rho(w, 32 - self.precision)
        if rho > self.registers[j]:
            self.registers[j] = rho

    def _rho(self, w: int, max_bits: int) -> int:
        if w == 0:
            return max_bits + 1
        val = bin(w)[2:].zfill(max_bits)
        return val.index("1") + 1

    def estimate_cardinality(self) -> float:
        m = self.m
        alpha = 0.7213 / (1.0 + 1.079 / m) if m >= 128 else 0.673
        raw_sum = sum(2.0 ** (-r) for r in self.registers)
        if raw_sum == 0:
            return 0.0
        estimate = alpha * (m**2) / raw_sum

        # Small range correction (LinearCounting)
        if estimate <= 2.5 * m:
            zeros = self.registers.count(0)
            if zeros > 0:
                estimate = m * math.log(m / zeros)
        return float(estimate)

    def merge(self, other: "HyperLogLogDigest") -> "HyperLogLogDigest":
        if self.precision != other.precision:
            raise ValueError("Cannot merge HyperLogLog digests with different precisions.")
        new_registers = [max(a, b) for a, b in zip(self.registers, other.registers)]
        return HyperLogLogDigest(precision=self.precision, registers=new_registers)

    def serialize(self) -> str:
        data = {"precision": self.precision, "registers": self.registers}
        return json.dumps(data)

    @classmethod
    def deserialize(cls, data_str: str) -> "HyperLogLogDigest":
        data = json.loads(data_str)
        return cls(precision=data["precision"], registers=data["registers"])


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
