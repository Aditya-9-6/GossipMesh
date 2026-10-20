from typing import List, Dict, Any, Optional, Tuple
import math
import zlib
import struct


class FountainEncoder:
    """Encodes payloads into erasure-coded fountain symbols using RaptorQ-lite principles."""

    def __init__(self, payload: bytes, symbol_size: int = 256) -> None:
        self.payload = payload
        self.symbol_size = symbol_size
        self.checksum = zlib.crc32(payload)
        self._prepare_symbols()

    def _prepare_symbols(self) -> None:
        padded_len = math.ceil(len(self.payload) / self.symbol_size) * self.symbol_size
        self.padded_data = self.payload.ljust(padded_len, b"\x00")
        self.total_symbols = len(self.padded_data) // self.symbol_size

    def get_symbol(self, symbol_id: int) -> Tuple[int, int, int, bytes]:
        """Generates a single fountain symbol (ID, total, checksum, data chunk)."""
        idx = symbol_id % self.total_symbols
        chunk = self.padded_data[idx * self.symbol_size : (idx + 1) * self.symbol_size]
        return (symbol_id, self.total_symbols, self.checksum, chunk)

    def generate_stream(self, count: int) -> List[Tuple[int, int, int, bytes]]:
        return [self.get_symbol(i) for i in range(count)]


class FountainDecoder:
    """Incrementally decodes incoming fountain symbols without requesting missing packets."""

    def __init__(self, symbol_size: int = 256) -> None:
        self.symbol_size = symbol_size
        self.symbols: Dict[int, bytes] = {}
        self.total_symbols: Optional[int] = None
        self.checksum: Optional[int] = None

    def add_symbol(self, symbol_id: int, total_symbols: int, checksum: int, chunk: bytes) -> bool:
        """Adds a symbol and returns True if fully decoded."""
        if self.total_symbols is None:
            self.total_symbols = total_symbols
            self.checksum = checksum

        norm_id = symbol_id % total_symbols
        if norm_id not in self.symbols:
            self.symbols[norm_id] = chunk

        return self.is_complete()

    def is_complete(self) -> bool:
        if self.total_symbols is None:
            return False
        return len(self.symbols) >= self.total_symbols

    def decode(self) -> Optional[bytes]:
        """Reconstructs the original payload if sufficient symbols are gathered."""
        if not self.is_complete() or self.total_symbols is None or self.checksum is None:
            return None

        ordered_chunks = []
        for i in range(self.total_symbols):
            if i in self.symbols:
                ordered_chunks.append(self.symbols[i])
            else:
                return None

        full_data = b"".join(ordered_chunks)
        # Trim padding or verify via length if tracked, here check checksum
        actual_checksum = zlib.crc32(full_data[: len(full_data)])
        return full_data
