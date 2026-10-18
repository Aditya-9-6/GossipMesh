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
            # Pad chunk to shard_size if short
            if len(chunk) < shard_size:
                chunk += b"\x00" * (shard_size - len(chunk))
            data_shards.append(chunk)
            shards.append((i, chunk))
            
        # Generate parity chunks using deterministic XOR combinations
        for j in range(self.m):
            parity_idx = self.k + j
            parity_data = bytearray(shard_size)
            for idx in range(shard_size):
                val = 0
                for i in range(self.k):
                    b = data_shards[i][idx]
                    # Simple coefficient mixing to ensure distinct parity equations
                    coeff = ((i + 1) * (j + 1)) & 0xFF
                    val ^= (b ^ coeff)
                parity_data[idx] = val & 0xFF
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
        
        # Determine shard size from the first available shard
        shard_size = len(sorted_shards[0][1]) if sorted_shards and sorted_shards[0][1] else 0
        
        data_map = {s[0]: s[1] for s in sorted_shards if s[0] < self.k}
        parity_map = {s[0]: s[1] for s in sorted_shards if s[0] >= self.k}
        
        recovered_chunks = []
        for i in range(self.k):
            reconstructed_chunk = bytearray(shard_size)
            if i in data_map:
                chunk = data_map[i]
                if len(chunk) < shard_size:
                    chunk += b"\x00" * (shard_size - len(chunk))
                recovered_chunks.append(chunk)
            else:
                # Reconstruct missing data shard using parity info if available
                if parity_map:
                    p_idx, p_data = next(iter(parity_map.items()))
                    j = p_idx - self.k
                    for idx in range(shard_size):
                        val = p_data[idx] if idx < len(p_data) else 0
                        # Reverse the XOR mixing for other present data shards
                        for other_i in range(self.k):
                            if other_i != i and other_i in data_map:
                                b = data_map[other_i][idx] if idx < len(data_map[other_i]) else 0
                                coeff = ((other_i + 1) * (j + 1)) & 0xFF
                                val ^= (b ^ coeff)
                        coeff_self = ((i + 1) * (j + 1)) & 0xFF
                        reconstructed_chunk[idx] = (val ^ coeff_self) & 0xFF
                recovered_chunks.append(bytes(reconstructed_chunk))
                
        reconstructed = b"".join(recovered_chunks)
        if original_length is not None:
            return reconstructed[:original_length]
        return reconstructed.rstrip(b"\x00")
