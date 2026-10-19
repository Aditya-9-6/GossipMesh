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
                for i in range(len(buf)):
                    buf[i] = 0
                return buf
        return bytearray(self.block_size)

    def release(self, buf: bytearray) -> None:
        if len(buf) != self.block_size:
            return
        with self._lock:
            if len(self._pool) < self.max_pool_size:
                for i in range(len(buf)):
                    buf[i] = 0
                self._pool.append(buf)


class GF28Arithmetic:
    """Galois Field GF(2^8) arithmetic operations with primitive polynomial x^8 + x^4 + x^3 + x^2 + 1 (0x11d)."""

    _INIT = False
    _EXP = [0] * 512
    _LOG = [0] * 256

    @classmethod
    def _init_tables(cls) -> None:
        if cls._INIT:
            return
        x = 1
        for i in range(255):
            cls._EXP[i] = x
            cls._LOG[x] = i
            x <<= 1
            if x & 0x100:
                x ^= 0x11D
        for i in range(255, 510):
            cls._EXP[i] = cls._EXP[i - 255]
        cls._LOG[0] = 0
        cls._INIT = True

    @classmethod
    def mul(cls, a: int, b: int) -> int:
        if not cls._INIT:
            cls._init_tables()
        if a == 0 or b == 0:
            return 0
        return cls._EXP[cls._LOG[a] + cls._LOG[b]]

    @classmethod
    def div(cls, a: int, b: int) -> int:
        if not cls._INIT:
            cls._init_tables()
        if a == 0:
            return 0
        if b == 0:
            raise ZeroDivisionError("Division by zero in GF(2^8)")
        return cls._EXP[(cls._LOG[a] - cls._LOG[b]) % 255]

    @classmethod
    def inverse(cls, a: int) -> int:
        return cls.div(1, a)


class ErasureCoder:
    """Reed-Solomon systematic erasure coder over GF(2^8) supporting k data blocks and m parity blocks."""

    def __init__(self, k: int = 4, m: int = 2, block_size: int = 1024) -> None:
        self.k = k
        self.m = m
        self.block_size = block_size
        self.pool = BlockPool(block_size=block_size)
        GF28Arithmetic._init_tables()

    def _vandermonde_row(self, row_idx: int, size: int) -> List[int]:
        # Generate Cauchy/Vandermonde row elements in GF(2^8)
        row = []
        for col_idx in range(size):
            # Avoid zero base elements to ensure invertibility
            base = (col_idx + 1) ^ (row_idx * 17)
            if base == 0:
                base = 1
            val = 1
            acc = 1
            power = row_idx + 1
            for _ in range(power):
                acc = GF28Arithmetic.mul(acc, base)
            row.append(acc)
        return row

    def encode(self, payload: bytes) -> List[Tuple[int, bytes]]:
        total_data_len = len(payload)
        required_capacity = self.k * self.block_size

        padded = bytearray(payload)
        if len(padded) < required_capacity:
            padded.extend(b"\x00" * (required_capacity - len(padded)))

        data_blocks: List[bytearray] = []
        for i in range(self.k):
            start = i * self.block_size
            end = start + self.block_size
            block = self.pool.acquire()
            block[: len(padded[start:end])] = padded[start:end]
            data_blocks.append(block)

        parity_blocks: List[bytearray] = []
        for j in range(self.m):
            p_block = self.pool.acquire()
            row = self._vandermonde_row(j, self.k)
            for b_idx in range(self.block_size):
                acc = 0
                for i in range(self.k):
                    term = GF28Arithmetic.mul(row[i], data_blocks[i][b_idx])
                    acc ^= term
                p_block[b_idx] = acc
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

    def _invert_matrix(self, matrix: List[List[int]]) -> List[List[int]]:
        n = len(matrix)
        inv = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
        mat = [row[:] for row in matrix]

        for i in range(n):
            pivot = mat[i][i]
            if pivot == 0:
                for r in range(i + 1, n):
                    if mat[r][i] != 0:
                        mat[i], mat[r] = mat[r], mat[i]
                        inv[i], inv[r] = inv[r], inv[i]
                        pivot = mat[i][i]
                        break
            if pivot == 0:
                raise ValueError("Singular matrix encountered during erasure decoding inversion")

            inv_pivot = GF28Arithmetic.inverse(pivot)
            for c in range(n):
                mat[i][c] = GF28Arithmetic.mul(mat[i][c], inv_pivot)
                inv[i][c] = GF28Arithmetic.mul(inv[i][c], inv_pivot)

            for r in range(n):
                if r != i:
                    factor = mat[r][i]
                    if factor != 0:
                        for c in range(n):
                            mat[r][c] ^= GF28Arithmetic.mul(factor, mat[i][c])
                            inv[r][c] ^= GF28Arithmetic.mul(factor, inv[i][c])
        return inv

    def decode(self, fragments: List[Tuple[int, bytes]], original_size: Optional[int] = None) -> bytes:
        if len(fragments) < self.k:
            raise ValueError(f"Insufficient fragments for reconstruction: got {len(fragments)}, required {self.k}")

        active_frags = fragments[: self.k]
        available_map = {idx: content for idx, content in active_frags}

        # Check if all systematic data blocks are present
        all_systematic_present = all(i in available_map for i in range(self.k))
        if all_systematic_present:
            reconstructed = bytearray()
            for i in range(self.k):
                reconstructed.extend(available_map[i])
            if original_size is not None:
                return bytes(reconstructed[:original_size])
            return bytes(reconstructed).rstrip(b"\x00")

        # Construct encoding sub-matrix corresponding to available fragments
        sub_matrix: List[List[int]] = []
        rhs_blocks: List[bytearray] = []

        for idx, content in active_frags:
            block = bytearray(self.block_size)
            block[: len(content)] = content
            rhs_blocks.append(block)

            if idx < self.k:
                row = [1 if c == idx else 0 for c in range(self.k)]
            else:
                parity_row_idx = idx - self.k
                row = self._vandermonde_row(parity_row_idx, self.k)
            sub_matrix.append(row)

        try:
            inv_matrix = self._invert_matrix(sub_matrix)
        except Exception as e:
            raise ValueError(f"Failed to invert Vandermonde matrix for erasure decoding: {e}") from e

        decoded_data_blocks: List[bytearray] = [bytearray(self.block_size) for _ in range(self.k)]
        for i in range(self.k):
            for b_idx in range(self.block_size):
                acc = 0
                for r_idx in range(self.k):
                    factor = inv_matrix[i][r_idx]
                    val = rhs_blocks[r_idx][b_idx]
                    acc ^= GF28Arithmetic.mul(factor, val)
                decoded_data_blocks[i][b_idx] = acc

        reconstructed = bytearray()
        for block in decoded_data_blocks:
            reconstructed.extend(block)

        if original_size is not None:
            return bytes(reconstructed[:original_size])

        return bytes(reconstructed).rstrip(b"\x00")
