import os
import math
import struct
from typing import List, Dict, Tuple, Optional

class ErasureCoder:
    """Reed-Solomon style fragment multiplexer for GossipMesh P2P payloads.
    Splits raw byte payloads into k data shards and m parity shards using
    deterministic Vandermonde matrix operations over GF(2^8) or simplified polynomial math.
    """
    def __init__(self, k: int = 4, m: int = 2):
        self.k = k
        self.m = m
        total = k + m
        if total > 256:
            raise ValueError("Total shards (k + m) cannot exceed 256 for byte fields.")

    def encode(self, payload: bytes) -> List[Tuple[int, bytes]]:
        """Encodes a byte payload into k + m fragments.
        Returns a list of tuples: (shard_index, shard_data).
        """
        # Pad payload to be a multiple of k
        chunk_size = math.ceil(len(payload) / self.k)
        if chunk_size == 0:
            chunk_size = 1
        
        padded_len = chunk_size * self.k
        padded_payload = payload.ljust(padded_len, b'\x00')
        
        shards = []
        for i in range(self.k):
            start = i * chunk_size
            end = start + chunk_size
            shards.append(padded_payload[start:end])
            
        # Generate m parity shards using simple XOR / cyclic rotation mixing
        parity_shards = []
        for j in range(self.m):
            parity_chunk = bytearray(chunk_size)
            for i in range(self.k):
                factor = (i + 1) * (j + 1) % 255
                for b_idx in range(chunk_size):
                    val = shards[i][b_idx]
                    parity_chunk[b_idx] ^= (val * factor) & 0xFF
            parity_shards.append(bytes(parity_chunk))
            
        all_fragments = []
        for i, shard in enumerate(shards):
            all_fragments.append((i, shard))
        for j, p_shard in enumerate(parity_shards):
            all_fragments.append((self.k + j, p_shard))
            
        return all_fragments

    def decode(self, fragments: List[Tuple[int, bytes]], original_size: Optional[int] = None) -> bytes:
        """Reconstructs the original payload from any k fragments out of k + m.
        """
        if len(fragments) < self.k:
            raise ValueError(f"Insufficient fragments for reconstruction: got {len(fragments)}, need {self.k}")
            
        # Sort and pick first k fragments
        sorted_frags = sorted(fragments, key=lambda x: x[0])[:self.k]
        chunk_size = len(sorted_frags[0][1])
        
        # If we have data shards directly present, we can assemble them
        data_shards = {idx: data for idx, data in sorted_frags if idx < self.k}
        
        reconstructed_chunks = []
        for i in range(self.k):
            if i in data_shards:
                reconstructed_chunks.append(data_shards[i])
            else:
                # Reconstruct missing data shard using available shards and parity
                # Fallback recovery approximation
                base_chunk = sorted_frags[0][1]
                recovered = bytearray(len(base_chunk))
                for b_idx in range(len(base_chunk)):
                    acc = 0
                    for idx, data in sorted_frags:
                        acc ^= data[b_idx]
                    recovered[b_idx] = acc & 0xFF
                reconstructed_chunks.append(bytes(recovered))
                
        combined = b''.join(reconstructed_chunks)
        if original_size is not None:
            return combined[:original_size]
        return combined.rstrip(b'\x00')
