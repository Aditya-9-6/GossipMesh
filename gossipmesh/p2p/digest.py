import math
import json
from typing import List, Dict, Any, Optional

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
        h = (h ^ (h >> 16)) * 0x85ebca6b
        h = (h ^ (h >> 13)) * 0xc2b2ae35
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
        return val.index('1') + 1

    def estimate_cardinality(self) -> float:
        m = self.m
        alpha = 0.7213 / (1.0 + 1.079 / m) if m >= 128 else 0.673
        raw_sum = sum(2.0 ** (-r) for r in self.registers)
        if raw_sum == 0:
            return 0.0
        estimate = alpha * (m ** 2) / raw_sum
        
        # Small range correction (LinearCounting)
        if estimate <= 2.5 * m:
            zeros = self.registers.count(0)
            if zeros > 0:
                estimate = m * math.log(m / zeros)
        return float(estimate)

    def merge(self, other: 'HyperLogLogDigest') -> 'HyperLogLogDigest':
        if self.precision != other.precision:
            raise ValueError("Cannot merge HyperLogLog digests with different precisions.")
        new_registers = [max(a, b) for a, b in zip(self.registers, other.registers)]
        return HyperLogLogDigest(precision=self.precision, registers=new_registers)

    def serialize(self) -> str:
        data = {
            "precision": self.precision,
            "registers": self.registers
        }
        return json.dumps(data)

    @classmethod
    def deserialize(cls, data_str: str) -> 'HyperLogLogDigest':
        data = json.loads(data_str)
        return cls(precision=data["precision"], registers=data["registers"])
