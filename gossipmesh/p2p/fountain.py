import math
import zlib
import struct
from typing import List, Dict, Tuple, Optional

class FountainEncoder:
    def __init__(self, payload: bytes, symbol_size: int = 64):
        self.payload = payload
        self.symbol_size = max(1, symbol_size)
        self.compressed = zlib.compress(payload)
        self.symbols = self._chunk_data(self.compressed)
        
    def _chunk_data(self, data: bytes) -> List[bytes]:
        chunks = []
        for i in range(0, len(data), self.symbol_size):
            chunk = data[i:i + self.symbol_size]
            if len(chunk) < self.symbol_size:
                chunk = chunk + b'\x00' * (self.symbol_size - len(chunk))
            chunks.append(chunk)
        return chunks

    def generate_symbol(self, seq: int) -> Tuple[int, int, bytes]:
        total = len(self.symbols)
        if total == 0:
            return (0, 0, b'\x00' * self.symbol_size)
        idx = seq % total
        return (seq, total, self.symbols[idx])

class FountainDecoder:
    def __init__(self, total_symbols: int, symbol_size: int = 64):
        self.total_symbols = total_symbols
        self.symbol_size = symbol_size
        self.received: Dict[int, bytes] = {}

    def add_symbol(self, seq: int, symbol: bytes) -> bool:
        if seq not in self.received and len(self.received) < self.total_symbols:
            self.received[seq] = symbol
        return len(self.received) >= self.total_symbols

    def is_complete(self) -> bool:
        return len(self.received) >= self.total_symbols

    def decode(self) -> Optional[bytes]:
        if not self.is_complete():
            return None
        sorted_symbols = [self.received[i] for i in range(self.total_symbols) if i in self.received]
        if len(sorted_symbols) < self.total_symbols:
            return None
        combined = b''.join(sorted_symbols)
        try:
            return zlib.decompress(combined)
        except Exception:
            return None
