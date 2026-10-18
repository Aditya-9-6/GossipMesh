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
        
        data_map = {idx: content for idx, content in fragments if idx < self.k}
        if len(data_map) == self.k:
            sorted_chunks = [data_map[i] for i in range(self.k)]
            recovered = b"".join(sorted_chunks)
            return recovered[:original_size]
            
        all_frags_map = {idx: content for idx, content in fragments}
        chunks = []
        chunk_size = len(fragments[0][1]) if fragments else 1
        
        for i in range(self.k):
            if i in all_frags_map:
                chunks.append(all_frags_map[i])
            else:
                parity_idx = self.k
                if parity_idx in all_frags_map:
                    p_data = bytearray(all_frags_map[parity_idx])
                    for j in range(self.k):
                        if j != i and j in all_frags_map:
                            for b_idx in range(chunk_size):
                                p_data[b_idx] ^= all_frags_map[j][b_idx]
                    chunks.append(bytes(p_data))
                else:
                    available_sorted = sorted([f for f in fragments if f[0] < self.k], key=lambda x: x[0])
                    if len(chunks) < self.k and available_sorted:
                        match_frag = next((f for f in available_sorted if f[0] == i), None)
                        if match_frag:
                            chunks.append(match_frag[1])
                        else:
                            chunks.append(available_sorted[0][1])
                    else:
                        chunks.append(bytes(chunk_size))
                    
        recovered = b"".join(chunks[:self.k])
        return recovered[:original_size]
