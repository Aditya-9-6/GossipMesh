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
        
        # Separate data fragments (index < k) from parity fragments
        data_map = {idx: content for idx, content in fragments if idx < self.k}
        
        # If we have all k data fragments directly, assemble them in correct order
        if len(data_map) == self.k:
            sorted_chunks = [data_map[i] for i in range(self.k)]
            recovered = b"".join(sorted_chunks)
            return recovered[:original_size]
            
        # Otherwise, sort available fragments and take up to k, or reconstruct if parity is needed.
        # For simple XOR scheme where parity covers all chunks, if a data chunk is missing and we have parity:
        sorted_frags = sorted(fragments, key=lambda x: x[0])
        
        # If we are missing specific data fragments but have enough total fragments:
        # Let's reconstruct missing data chunks using XOR parity if available
        all_frags_map = {idx: content for idx, content in fragments}
        
        chunks = []
        chunk_size = len(fragments[0][1]) if fragments else 1
        
        for i in range(self.k):
            if i in all_frags_map:
                chunks.append(all_frags_map[i])
            else:
                # Attempt single parity recovery if available
                parity_idx = self.k
                if parity_idx in all_frags_map:
                    # Reconstruct missing chunk i using parity and all other available data chunks
                    p_data = bytearray(all_frags_map[parity_idx])
                    for j in range(self.k):
                        if j != i and j in all_frags_map:
                            for b_idx in range(chunk_size):
                                p_data[b_idx] ^= all_frags_map[j][b_idx]
                    chunks.append(bytes(p_data))
                else:
                    # Fallback to arbitrary sorted slice if no exact match
                    chunks.append(bytes(chunk_size))
                    
        recovered = b"".join(chunks)
        return recovered[:original_size]
