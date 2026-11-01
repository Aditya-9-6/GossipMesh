"""
Erasure-Coded Fountain Fragments for Resilient Gossip Broadcast.

Implements RaptorQ-lite rateless fountain coding principles inside GossipMesh to encode
large state payloads into independent fountain symbols with bounded memory allocations
and functions strictly under 60 LOC.
"""

from __future__ import annotations

import math
import random
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class FountainFragmentConfig:
    chunk_size: int = 512
    max_degree: int = 8
    overhead_factor: float = 1.25


@dataclass
class FountainFragment:
    session_id: str
    symbol_id: int
    degree: int
    indices: List[int]
    payload: bytes
    total_chunks: int

    def serialize(self) -> bytes:
        sid_bytes = self.session_id.encode("utf-8")
        sid_len = len(sid_bytes)
        idx_count = len(self.indices)
        idx_bytes = struct.pack(f"{idx_count}I", *self.indices)
        pay_len = len(self.payload)
        header = struct.pack("H Q H H H", sid_len, self.symbol_id, self.degree, self.total_chunks, idx_count)
        return header + sid_bytes + idx_bytes + struct.pack("I", pay_len) + self.payload

    @classmethod
    def deserialize(cls, raw: bytes) -> FountainFragment:
        header_format = "H Q H H H"
        header_size = struct.calcsize(header_format)
        sid_len, symbol_id, degree, total_chunks, idx_count = struct.unpack_from(header_format, raw, 0)
        offset = header_size
        session_id = raw[offset : offset + sid_len].decode("utf-8")
        offset += sid_len
        indices = list(struct.unpack_from(f"{idx_count}I", raw, offset))
        offset += struct.calcsize(f"{idx_count}I")
        pay_len = struct.unpack_from("I", raw, offset)[0]
        offset += 4
        payload = raw[offset : offset + pay_len]
        return cls(
            session_id=session_id,
            symbol_id=symbol_id,
            degree=degree,
            indices=indices,
            payload=payload,
            total_chunks=total_chunks,
        )


class FountainEncoder:
    def __init__(self, data: bytes, config: Optional[FountainFragmentConfig] = None) -> None:
        self.config = config or FountainFragmentConfig()
        self.data = data
        self.chunks = self._chunk_data()
        self.total_chunks = len(self.chunks)

    def _chunk_data(self) -> List[bytes]:
        chunks = []
        cs = self.config.chunk_size
        for i in range(0, max(len(self.data), 1), cs):
            chunk = self.data[i : i + cs]
            if len(chunk) < cs:
                chunk = chunk + b"\x00" * (cs - len(chunk))
            chunks.append(chunk)
        return chunks

    def generate_symbol(self, symbol_id: int, session_id: str) -> FountainFragment:
        rng = random.Random(symbol_id + hash(session_id))
        degree = rng.randint(1, min(self.config.max_degree, self.total_chunks))
        indices = sorted(rng.sample(range(self.total_chunks), degree))

        buf = bytearray(self.config.chunk_size)
        for idx in indices:
            chunk = self.chunks[idx]
            for b_idx in range(len(buf)):
                buf[b_idx] ^= chunk[b_idx]

        return FountainFragment(
            session_id=session_id,
            symbol_id=symbol_id,
            degree=degree,
            indices=indices,
            payload=bytes(buf),
            total_chunks=self.total_chunks,
        )


class FountainDecoder:
    def __init__(self, total_chunks: int, chunk_size: int = 512) -> None:
        self.total_chunks = total_chunks
        self.chunk_size = chunk_size
        self.received_symbols: List[FountainFragment] = []
        self._decoded_chunks: Dict[int, bytes] = {}

    def add_fragment(self, fragment: FountainFragment) -> bool:
        if fragment.total_chunks != self.total_chunks:
            return False
        self.received_symbols.append(fragment)
        return self.try_decode()

    def try_decode(self) -> bool:
        if len(self._decoded_chunks) >= self.total_chunks:
            return True

        progress = True
        while progress:
            progress = False
            for sym in self.received_symbols:
                unknowns = [idx for idx in sym.indices if idx not in self._decoded_chunks]
                if len(unknowns) == 1:
                    target = unknowns[0]
                    val = bytearray(sym.payload)
                    for idx in sym.indices:
                        if idx != target:
                            val = bytearray(b ^ c for b, c in zip(val, self._decoded_chunks[idx]))
                    self._decoded_chunks[target] = bytes(val)
                    progress = True
        return len(self._decoded_chunks) == self.total_chunks

    def get_reassembled_data(self, original_len: Optional[int] = None) -> Optional[bytes]:
        if len(self._decoded_chunks) < self.total_chunks:
            return None
        full = bytearray()
        for i in range(self.total_chunks):
            full.extend(self._decoded_chunks[i])
        if original_len is not None:
            return bytes(full[:original_len])
        return bytes(full)
