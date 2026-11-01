import mmh3
import math
import threading
from typing import List, Union, Optional, Set


class BitsetFingerprint:
    def __init__(self, capacity: int, fp_rate: float = 0.01) -> None:
        self.capacity = max(1, capacity)
        self.fp_rate = max(0.0001, min(0.5, fp_rate))

        self.m = int(-(self.capacity * math.log(self.fp_rate)) / (math.log(2) ** 2))
        self.m = max(64, ((self.m + 63) // 64) * 64)
        self.k = max(1, int((self.m / self.capacity) * math.log(2)))

        self._bytes_len = self.m // 8
        self._bitset = bytearray(self._bytes_len)
        self._lock = threading.Lock()

    def add(self, item: str) -> None:
        with self._lock:
            for i in range(self.k):
                h = mmh3.hash(item, i, signed=False)
                idx = h % self.m
                self._bitset[idx // 8] |= 1 << (idx % 8)

    def __contains__(self, item: str) -> bool:
        with self._lock:
            for i in range(self.k):
                h = mmh3.hash(item, i, signed=False)
                idx = h % self.m
                if not (self._bitset[idx // 8] & (1 << (idx % 8))):
                    return False
            return True

    def to_bytes(self) -> bytes:
        with self._lock:
            return bytes(self._bitset)

    @classmethod
    def from_bytes(cls, data: bytes, capacity: int, fp_rate: float = 0.01) -> "BitsetFingerprint":
        inst = cls(capacity=capacity, fp_rate=fp_rate)
        inst._bitset = bytearray(data)
        return inst

    def union_inplace(self, other: "BitsetFingerprint") -> None:
        with self._lock, other._lock:
            for i in range(len(self._bitset)):
                self._bitset[i] |= other._bitset[i]
