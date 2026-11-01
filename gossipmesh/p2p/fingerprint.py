import mmh3
import math
import threading
from typing import List, Union, Optional


class BitsetFingerprint:
    def __init__(self, capacity: int, fp_rate: float = 0.01) -> None:
        self.capacity = max(1, capacity)
        self.fp_rate = max(0.0001, min(0.5, fp_rate))

        # Compute optimal bit array size m and hash count k
        self.m = int(-(self.capacity * math.log(self.fp_rate)) / (math.log(2) ** 2))
        self.m = max(64, ((self.m + 63) // 64) * 64)  # Align to 64-bit words
        self.k = max(1, int((self.m / self.capacity) * math.log(2)))

        self._bytes_len = self.m // 8
        self._bitset = bytearray(self._bytes_len)
        self._lock = threading.Lock()

    def _get_hash_indices(self, data: bytes) -> List[int]:
        # Use MurmurHash3 with 128-bit output split into two 64-bit values for double hashing (Kirsch-Mitzenmacher)
        h1, h2 = mmh3.hash128(data, signed=False), mmh3.hash128(data, seed=0x12345678, signed=False)
        indices = []
        for i in range(self.k):
            combined = (h1 + i * h2) % self.m
            indices.append(combined)
        return indices

    def add(self, data: Union[bytes, str]) -> None:
        if isinstance(data, str):
            data = data.encode("utf-8")
        indices = self._get_hash_indices(data)
        with self._lock:
            for idx in indices:
                byte_idx = idx >> 3
                bit_offset = idx & 7
                self._bitset[byte_idx] |= 1 << bit_offset

    def contains(self, data: Union[bytes, str]) -> bool:
        if isinstance(data, str):
            data = data.encode("utf-8")
        indices = self._get_hash_indices(data)
        with self._lock:
            for idx in indices:
                byte_idx = idx >> 3
                bit_offset = idx & 7
                if not (self._bitset[byte_idx] & (1 << bit_offset)):
                    return False
        return True

    def to_bytes(self) -> bytes:
        with self._lock:
            return bytes(self._bitset)

    @classmethod
    def from_bytes(cls, capacity: int, fp_rate: float, buffer: bytes) -> "BitsetFingerprint":
        filter_obj = cls(capacity, fp_rate)
        if len(buffer) != filter_obj._bytes_len:
            raise ValueError(f"Buffer length {len(buffer)} does not match expected size {filter_obj._bytes_len}")
        filter_obj._bitset = bytearray(buffer)
        return filter_obj

    def union_inplace(self, other: "BitsetFingerprint") -> None:
        if self.m != other.m:
            raise ValueError("Cannot union filters with differing sizes")
        with self._lock, other._lock:
            # Vectorized byte-wise OR operation
            for i in range(self._bytes_len):
                self._bitset[i] |= other._bitset[i]
