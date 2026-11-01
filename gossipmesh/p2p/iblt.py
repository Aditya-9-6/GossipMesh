import zlib
import struct
from typing import Set, Tuple, List, Optional


class IBLTCell:
    __slots__ = ("count", "key_sum", "key_hash_sum")

    def __init__(self, count: int = 0, key_sum: int = 0, key_hash_sum: int = 0):
        self.count = count
        self.key_sum = key_sum
        self.key_hash_sum = key_hash_sum

    def is_empty(self) -> bool:
        return self.count == 0 and self.key_sum == 0 and self.key_hash_sum == 0

    def is_pure(self) -> bool:
        if self.count == 1 or self.count == -1:
            expected_hash = zlib.crc32(struct.pack("!Q", self.key_sum)) & 0xFFFFFFFF
            return expected_hash == self.key_hash_sum
        return False


class InvertibleBloomLookupTable:
    def __init__(self, size: int = 64, hash_functions: int = 4):
        self.size = size
        self.hash_functions = hash_functions
        self.table: List[IBLTCell] = [IBLTCell() for _ in range(size)]

    def _get_indices_and_hashes(self, key: int) -> List[Tuple[int, int]]:
        results = []
        b = struct.pack("!Q", key)
        for i in range(self.hash_functions):
            salt = struct.pack("!I", i)
            h = zlib.crc32(b + salt) & 0xFFFFFFFF
            idx = h % self.size
            key_hash = zlib.crc32(b) & 0xFFFFFFFF
            results.append((idx, key_hash))
        return results

    def insert(self, key: int) -> None:
        for idx, key_hash in self._get_indices_and_hashes(key):
            cell = self.table[idx]
            cell.count += 1
            cell.key_sum ^= key
            cell.key_hash_sum ^= key_hash

    def delete(self, key: int) -> None:
        for idx, key_hash in self._get_indices_and_hashes(key):
            cell = self.table[idx]
            cell.count -= 1
            cell.key_sum ^= key
            cell.key_hash_sum ^= key_hash

    def list_entries(self) -> Tuple[Set[int], Set[int]]:
        clone = InvertibleBloomLookupTable(self.size, self.hash_functions)
        for i, cell in enumerate(self.table):
            clone.table[i] = IBLTCell(cell.count, cell.key_sum, cell.key_hash_sum)

        positive_keys: Set[int] = set()
        negative_keys: Set[int] = set()

        while True:
            pure_found = False
            for i in range(clone.size):
                cell = clone.table[i]
                if cell.is_pure():
                    key = cell.key_sum
                    if cell.count == 1:
                        positive_keys.add(key)
                        clone.delete(key)
                    elif cell.count == -1:
                        negative_keys.add(key)
                        clone.insert(key)
                    pure_found = True
            if not pure_found:
                break

        for cell in clone.table:
            if not cell.is_empty():
                raise ValueError("IBLT could not be fully decoded due to high entropy or insufficient capacity")

        return positive_keys, negative_keys

    def subtract(self, other: "InvertibleBloomLookupTable") -> "InvertibleBloomLookupTable":
        if self.size != other.size or self.hash_functions != other.hash_functions:
            raise ValueError("Cannot subtract IBLTs of differing sizes or hash counts")
        result = InvertibleBloomLookupTable(self.size, self.hash_functions)
        for i in range(self.size):
            c1 = self.table[i]
            c2 = other.table[i]
            result.table[i] = IBLTCell(
                count=c1.count - c2.count,
                key_sum=c1.key_sum ^ c2.key_sum,
                key_hash_sum=c1.key_hash_sum ^ c2.key_hash_sum,
            )
        return result
