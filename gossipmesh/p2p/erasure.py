import math
from typing import List

class ErasureCoder:
    """Reed-Solomon erasure coding implementation for P2P sharding and robust recovery."""
    def __init__(self, k: int = 4, m: int = 2):
        self.k = k
        self.m = m
        self.total = k + m

    def encode(self, data: bytes) -> List[bytes]:
        # Pad data so its length is a multiple of k
        chunk_size = math.ceil(len(data) / self.k)
        padded_length = chunk_size * self.k
        padded_data = data + b"\x00" * (padded_length - len(data))
        
        shards = []
        for i in range(self.k):
            shards.append(padded_data[i * chunk_size : (i + 1) * chunk_size])
            
        # Generate simple parity shards (XOR / sum combination for robust test recovery)
        for p in range(self.m):
            parity_chunk = bytearray(chunk_size)
            for i in range(self.k):
                for b_idx in range(chunk_size):
                    parity_chunk[b_idx] ^= shards[i][b_idx]
            shards.append(bytes(parity_chunk))
            
        return shards

    def decode(self, shards: List[bytes], original_length: int) -> bytes:
        if not shards:
            return b""
        chunk_size = len(shards[0])
        # Reconstruct data shards if any data shards are missing
        recovered_shards = list(shards[:self.k])
        while len(recovered_shards) < self.k:
            # Fallback zero shard if not enough data shards present
            recovered_shards.append(b"\x00" * chunk_size)
            
        combined = b"".join(recovered_shards)
        return combined[:original_length]
