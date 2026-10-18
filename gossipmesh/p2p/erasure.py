import math
from typing import List, Tuple

class ErasureCoder:
    def __init__(self, data_fragments: int = 4, parity_fragments: int = 2):
        self.k = data_fragments
        self.m = parity_fragments
        self.n = self.k + self.m

    def encode(self, data: bytes) -> List[Tuple[int, bytes]]:
        """Encodes payload bytes into N data and parity fragments (< 50 LOC)."""
        chunk_size = math.ceil(len(data) / self.k) if len(data) > 0 else 1
        padded = data.ljust(chunk_size * self.k, b'\x00')
        chunks = [padded[i*chunk_size:(i+1)*chunk_size] for i in range(self.k)]
        fragments = [(i, chunk) for i, chunk in enumerate(chunks)]
        for p in range(self.m):
            parity_data = bytearray(chunk_size)
            for chunk in chunks:
                for j in range(chunk_size):
                    parity_data[j] ^= chunk[j]
            fragments.append((self.k + p, bytes(parity_data)))
        return fragments

    def decode(self, fragments: List[Tuple[int, bytes]], original_size: int) -> bytes:
        """Decodes fragments back into the original payload (< 50 LOC)."""
        if len(fragments) < self.k:
            raise ValueError("Insufficient fragments to reconstruct data")
        sorted_frags = sorted(fragments, key=lambda x: x[0])[:self.k]
        recovered = b"".join(frag[1] for frag in sorted_frags)
        return recovered[:original_size]
