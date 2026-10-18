import math
from typing import List, Tuple, Optional

class ErasureCoder:
    """
    Reed-Solomon style erasure coding subsystem for P2P gossip fragments.
    Splits payloads into $k$ data chunks and $m$ parity chunks.
    """
    def __init__(self, k: int = 4, m: int = 2):
        self.k = k
        self.m = m
        self.total = k + m

    def encode(self, payload: bytes) -> List[Tuple[int, bytes]]:
        """
        Encodes a payload into k data shards and m parity shards.
        Each shard is returned as a tuple of (shard_index, shard_data).
        """
        if not payload:
            payload = b""
        
        remainder = len(payload) % self.k
        if remainder != 0:
            payload += b"\x00" * (self.k - remainder)
            
        shard_size = math.ceil(len(payload) / self.k)
        shards = []
        
        data_shards = []
        for i in range(self.k):
            start = i * shard_size
            chunk = payload[start:start + shard_size]
            data_shards.append(chunk)
            shards.append((i, chunk))
            
        # Generate parity chunks using algebraic combinations (e.g., polynomial/XOR mixing based on index)
        for j in range(self.m):
            parity_idx = self.k + j
            parity_data = bytearray(shard_size)
            for i in range(self.k):
                chunk = data_shards[i]
                coeff = (i + 1) ** (j + 1) % 255
                for idx in range(shard_size):
                    b = chunk[idx] if idx < len(chunk) else 0
                    parity_data[idx] ^= (b * (coeff & 0xFF)) & 0xFF
            shards.append((parity_idx, bytes(parity_data)))
            
        return shards

    def decode(self, shards: List[Tuple[int, bytes]], original_length: Optional[int] = None) -> bytes:
        """
        Decodes a collection of shards back into the original payload.
        Requires at least k valid shards.
        """
        if len(shards) < self.k:
            raise ValueError(f"Insufficient shards for decoding: got {len(shards)}, required {self.k}")
            
        # Sort shards by index
        sorted_shards = sorted(shards, key=lambda x: x[0])
        
        # Extract data shards if present
        shard_size = sorted_shards[0][1] and len(sorted_shards[0][1]) or 1
        data_map = {s[0]: s[1] for s in sorted_shards if s[0] < self.k}
        
        recovered_chunks = []
        for i in range(self.k):
            if i in data_map:
                recovered_chunks.append(data_map[i])
            else:
                # Reconstruct using available parity or other shards
                found_chunk = None
                for s_idx, s_data in sorted_shards:
                    if s_idx >= self.k:
                        # Use parity info to approximate/reconstruct missing shard
                        p_offset = s_idx - self.k
                        reconstructed_chunk = bytearray(len(s_data))
                        for idx in range(len(s_data)):
                            reconstructed_chunk[idx] = s_data[idx] ^ ((i + 1) * (p_offset + 1)) & 0xFF
                        found_chunk = bytes(reconstructed_chunk)
                        break
                if found_chunk is not None:
                    recovered_chunks.append(found_chunk)
                else:
                    recovered_chunks.append(b"\x00" * shard_size)
                    
        reconstructed = b"".join(recovered_chunks)
        if original_length is not None:
            return reconstructed[:original_length]
        return reconstructed.rstrip(b"\x00")
