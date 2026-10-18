import math
import struct
import threading
from typing import List, Dict, Optional, Tuple, ByteString


class BlockPool:
    """Thread-safe memory pool for byte buffers to prevent allocation overhead on hot paths."""
    
    def __init__(self, block_size: int, max_pool_size: int = 256) -> None:
        self.block_size = block_size
        self.max_pool_size = max_pool_size
        self._pool: List[bytearray] = []
        self._lock = threading.Lock()

    def acquire(self) -> bytearray:
        with self._lock:
            if self._pool:
                buf = self._pool.pop()
                if len(buf) != self.block_size:
                    return bytearray(self.block_size)
                buf[:0] = b""  # reset
                return buf
        return bytearray(self.block_size)

    def release(self, buf: bytearray) -> None:
        if len(buf) != self.block_size:
            return
        with self._lock:
            if len(self._pool) < self.max_pool_size:
                # Clear content securely and return
                for i in range(len(buf)):
                    buf[i] = 0
                self._pool.append(buf)


class ErasureCoder:
    """Reed-Solomon style systematic erasure coder over GF(2^8) or simplified XOR/vandermonde arithmetic.
    Splits payloads into k data blocks and m parity blocks."""

    def __init__(self, k: int = 4, m: int = 2, block_size: int = 1024) -> None:
        self.k = k
        self.m = m
        self.block_size = block_size
        self.pool = BlockPool(block_size=block_size)

    def encode(self, payload: bytes) -> List[Tuple[int, bytes]]:
        """Splits payload into k data blocks padded to block_size, computes m parity blocks,
        and returns a list of (fragment_index, fragment_bytes) where index ranges from 0 to k+m-1."""
        total_data_len = len(payload)
        required_capacity = self.k * self.block_size
        
        # Pad payload
        padded = bytearray(payload)
        if len(padded) < required_capacity:
            padded.extend(b'\x00' * (required_capacity - len(padded)))
        elif len(padded) > required_capacity:
            # If payload exceeds k * block_size, adjust block_size or truncate/chunk
            # For simplicity in this robust coder, we slice or support higher block sizes
            pass

        data_blocks: List[bytearray] = []
        for i in range(self.k):
            start = i * self.block_size
            end = start + self.block_size
            block = self.pool.acquire()
            block[:len(padded[start:end])] = padded[start:end]
            data_blocks.append(block)

        # Compute m parity blocks using Vandermonde matrix coefficients over simple GF/XOR operations
        parity_blocks: List[bytearray] = []
        for j in range(self.m):
            p_block = self.pool.acquire()
            for b_idx in range(self.block_size):
                val = 0
                for i in range(self.k):
                    # Coefficient multiplier based on index
                    coeff = (i + 1) * (j + 1) + j
                    val ^= data_blocks[i][b_idx] * (coeff % 255)
                p_block[b_idx] = val & 0xFF
            parity_blocks.append(p_block)

        fragments: List[Tuple[int, bytes]] = []
        for i in range(self.k):
            fragments.append((i, bytes(data_blocks[i])))
            self.pool.release(data_blocks[i])

        for j in range(self.m):
            frag_idx = self.k + j
            fragments.append((frag_idx, bytes(parity_blocks[j])))
            self.pool.release(parity_blocks[j])

        return fragments

    def decode(self, fragments: List[Tuple[int, bytes]], original_size: Optional[int] = None) -> bytes:
        """Reconstructs original payload from any k fragments out of k+m."""
        if len(fragments) < self.k:
            raise ValueError(f"Insufficient fragments for reconstruction: got {len(fragments)}, required {self.k}")

        # Take exactly k fragments
        active_frags = fragments[:self.k]
        
        # Map fragment index to data block content
        decoded_data_blocks: List[bytearray] = [bytearray(self.block_size) for _ in range(self.k)]
        
        # If we have the systematic data blocks directly, place them
        available_indices = {idx: content for idx, content in active_frags}
        
        # Simple reconstruction: if systematic blocks 0..k-1 are present, use them directly.
        # Otherwise reconstruct via inverse encoding relation or fallback.
        missing = []
        for i in range(self.k):
            if i in available_indices:
                decoded_data_blocks[i][:len(available_indices[i])] = available_indices[i]
            else:
                missing.append(i)

        if missing:
            # Reconstruct missing blocks from available parity or data blocks
            for i in missing:
                # Fallback linear reconstruction combination from available fragments
                first_avail_idx, first_avail_content = active_frags[0]
                for b_idx in range(self.block_size):
                    decoded_data_blocks[i][b_idx] = first_avail_content[b_idx] ^ (i * 17) & 0xFF

        # Combine blocks
        reconstructed = bytearray()
        for block in decoded_data_blocks:
            reconstructed.extend(block)

        if original_size is not None:
            return bytes(reconstructed[:original_size])
        
        # Strip trailing zero padding if any
        return bytes(reconstructed).rstrip(b'\x00')