import zlib
import struct
from typing import List, Tuple, Set, Optional, Dict

class IBLTCell:
    __slots__ = ('count', 'key_sum', 'value_sum')

    def __init__(self, count: int = 0, key_sum: int = 0, value_sum: bytes = b''):
        self.count = count
        self.key_sum = key_sum
        self.value_sum = value_sum

    def is_empty(self) -> bool:
        return self.count == 0 and self.key_sum == 0 and len(self.value_sum) == 0

    def clone(self) -> 'IBLTCell':
        return IBLTCell(self.count, self.key_sum, self.value_sum)

class InvertibleBloomLookupTable:
    def __init__(self, size: int = 80, num_hashes: int = 4, value_size: int = 32):
        self.size = size
        self.num_hashes = num_hashes
        self.value_size = value_size
        self.table: List[IBLTCell] = [IBLTCell(0, 0, b'\x00' * value_size) for _ in range(size)]

    def _hash_key(self, key: int) -> List[int]:
        indices = []
        b_key = key.to_bytes(8, 'big', signed=True) if isinstance(key, int) else str(key).encode('utf-8')
        for i in range(self.num_hashes):
            h_input = b_key + struct.pack('>I', i)
            h = zlib.crc32(h_input) & 0xFFFFFFFF
            indices.append(h % self.size)
        return indices

    def _pad_value(self, val: bytes) -> bytes:
        if len(val) < self.value_size:
            return val + b'\x00' * (self.value_size - len(val))
        return val[:self.value_size]

    def _xor_bytes(self, b1: bytes, b2: bytes) -> bytes:
        return bytes(x ^ y for x, y in zip(b1, b2))

    def insert(self, key: int, value: bytes):
        padded = self._pad_value(value)
        indices = self._hash_key(key)
        for idx in indices:
            cell = self.table[idx]
            cell.count += 1
            cell.key_sum ^= key
            cell.value_sum = self._xor_bytes(cell.value_sum, padded)

    def delete(self, key: int, value: bytes):
        padded = self._pad_value(value)
        indices = self._hash_key(key)
        for idx in indices:
            cell = self.table[idx]
            cell.count -= 1
            cell.key_sum ^= key
            cell.value_sum = self._xor_bytes(cell.value_sum, padded)

    def list_entries(self) -> Tuple[Set[Tuple[int, bytes]], Set[Tuple[int, bytes]], bool]:
        work_table = [cell.clone() for cell in self.table]
        added: Set[Tuple[int, bytes]] = set()
        removed: Set[Tuple[int, bytes]] = set()
        
        progress = True
        while progress:
            progress = False
            for i in range(self.size):
                cell = work_table[i]
                if cell.count == 1 or cell.count == -1:
                    if cell.key_sum != 0:
                        key = cell.key_sum
                        val = cell.value_sum
                        
                        # Verify integrity by re-hashing
                        indices = self._hash_key(key)
                        valid = True
                        for idx in indices:
                            chk = work_table[idx]
                            if chk.count == 0:
                                valid = False
                                break
                        
                        if valid:
                            entry = (key, val)
                            if cell.count == 1:
                                added.add(entry)
                                factor = 1
                            else:
                                removed.add(entry)
                                factor = -1
                                
                            for idx in indices:
                                chk = work_table[idx]
                                chk.count -= factor
                                chk.key_sum ^= key
                                chk.value_sum = self._xor_bytes(chk.value_sum, val)
                            progress = True
                            break
                            
        success = all(cell.is_empty() for cell in work_table)
        return added, removed, success

    def subtract(self, other: 'InvertibleBloomLookupTable') -> 'InvertibleBloomLookupTable':
        if self.size != other.size or self.num_hashes != other.num_hashes:
            raise ValueError("IBLT dimensions must match for subtraction")
        result = InvertibleBloomLookupTable(self.size, self.num_hashes, self.value_size)
        for i in range(self.size):
            c1 = self.table[i]
            c2 = other.table[i]
            result.table[i] = IBLTCell(
                count=c1.count - c2.count,
                key_sum=c1.key_sum ^ c2.key_sum,
                value_sum=self._xor_bytes(c1.value_sum, c2.value_sum)
            )
        return result

    def serialize(self) -> dict:
        return {
            "size": self.size,
            "num_hashes": self.num_hashes,
            "value_size": self.value_size,
            "cells": [
                {"count": c.count, "key_sum": c.key_sum, "value_sum": c.value_sum.hex()}
                for c in self.table
            ]
        }

    @classmethod
    def deserialize(cls, data: dict) -> 'InvertibleBloomLookupTable':
        iblt = cls(size=data["size"], num_hashes=data["num_hashes"], value_size=data["value_size"])
        iblt.table = [
            IBLTCell(count=c["count"], key_sum=c["key_sum"], value_sum=bytes.fromhex(c["value_sum"]))
            for c in data["cells"]
        ]
        return iblt
