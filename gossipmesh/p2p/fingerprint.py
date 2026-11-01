import hashlib
import struct


class BitsetFingerprint:
    def __init__(self, capacity: int = 1000, fp_rate: float = 0.01):
        self.capacity = capacity
        self.fp_rate = fp_rate
        self.size = max(64, capacity * 2)
        self.bitset = bytearray((self.size + 7) // 8)

    def _hash(self, item: str | bytes) -> int:
        if isinstance(item, str):
            item = item.encode("utf-8")
        h = hashlib.sha256(item).digest()
        return struct.unpack(">I", h[:4])[0] % self.size

    def add(self, item: str | bytes) -> None:
        idx = self._hash(item)
        self.bitset[idx // 8] |= 1 << (idx % 8)

    def contains(self, item: str | bytes) -> bool:
        idx = self._hash(item)
        return bool(self.bitset[idx // 8] & (1 << (idx % 8)))

    def to_bytes(self) -> bytes:
        return bytes(self.bitset)

    @classmethod
    def from_bytes(cls, capacity: int, fp_rate: float, buffer: bytes) -> "BitsetFingerprint":
        inst = cls(capacity=capacity, fp_rate=fp_rate)
        inst.bitset = bytearray(buffer)
        return inst

    def union_inplace(self, other: "BitsetFingerprint") -> None:
        for i in range(len(self.bitset)):
            self.bitset[i] |= other.bitset[i]
