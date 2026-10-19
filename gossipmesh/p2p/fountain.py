import os
import random
import math
from typing import List, Dict, Tuple, Optional


class FountainEncoder:
    """Encodes a byte payload into randomized linear fountain chunks (RLNC)."""

    def __init__(self, data: bytes, chunk_size: int = 64, field_size: int = 256):
        self.data = data
        self.chunk_size = chunk_size
        self.field_size = field_size
        self.chunks = self._split_data()
        self.k = len(self.chunks)

    def _split_data(self) -> List[bytes]:
        chunks = []
        for i in range(0, len(self.data), self.chunk_size):
            chunk = self.data[i : i + self.chunk_size]
            if len(chunk) < self.chunk_size:
                chunk = chunk + b"\x00" * (self.chunk_size - len(chunk))
            chunks.append(chunk)
        if not chunks:
            chunks.append(b"\x00" * self.chunk_size)
        return chunks

    def generate_packet(self) -> Tuple[List[int], bytes]:
        actual_field_size = min(self.field_size, 256)
        coeffs = [random.randint(1, max(1, actual_field_size - 1)) for _ in range(self.k)]
        coded_chunk = [0] * self.chunk_size
        for i, coeff in enumerate(coeffs):
            chunk = self.chunks[i]
            for b_idx in range(self.chunk_size):
                val = (coded_chunk[b_idx] + coeff * chunk[b_idx]) % actual_field_size
                coded_chunk[b_idx] = val & 0xFF
        return coeffs, bytes(coded_chunk)


class FountainDecoder:
    """Decodes incoming randomized linear fountain chunks using Gaussian elimination."""

    def __init__(self, k: int, chunk_size: int = 64, field_size: int = 256):
        self.k = k
        self.chunk_size = chunk_size
        self.field_size = min(field_size, 256)
        self.received_coeffs: List[List[int]] = []
        self.received_chunks: List[bytearray] = []

    def add_packet(self, coeffs: List[int], chunk: bytes) -> bool:
        if len(coeffs) != self.k or len(chunk) != self.chunk_size:
            return False

        working_coeffs = list(coeffs)
        working_chunk = bytearray(chunk)

        for i in range(min(len(self.received_coeffs), self.k)):
            existing_coeffs = self.received_coeffs[i]
            pivot = -1
            for idx, c in enumerate(existing_coeffs):
                if c != 0:
                    pivot = idx
                    break
            if pivot != -1 and working_coeffs[pivot] != 0:
                factor = working_coeffs[pivot]
                for j in range(self.k):
                    working_coeffs[j] = (working_coeffs[j] - factor * existing_coeffs[j]) % self.field_size
                existing_chunk = self.received_chunks[i]
                for b_idx in range(self.chunk_size):
                    working_chunk[b_idx] = (working_chunk[b_idx] - factor * existing_chunk[b_idx]) % self.field_size

        first_non_zero = -1
        for idx, c in enumerate(working_coeffs):
            if c != 0:
                first_non_zero = idx
                break

        if first_non_zero == -1:
            return False

        inv = self._mod_inverse(working_coeffs[first_non_zero], self.field_size)
        if inv is None:
            return False

        for j in range(self.k):
            working_coeffs[j] = (working_coeffs[j] * inv) % self.field_size
        for b_idx in range(self.chunk_size):
            working_chunk[b_idx] = (working_chunk[b_idx] * inv) % self.field_size

        self.received_coeffs.append(working_coeffs)
        self.received_chunks.append(working_chunk)
        return True

    def _mod_inverse(self, a: int, m: int) -> Optional[int]:
        a = a % m
        for x in range(1, m):
            if (a * x) % m == 1:
                return x
        return None

    def is_complete(self) -> bool:
        return len(self.received_coeffs) >= self.k

    def decode(self) -> Optional[bytes]:
        if not self.is_complete():
            return None

        matrix_c = [list(row) for row in self.received_coeffs[: self.k]]
        matrix_v = [bytearray(row) for row in self.received_chunks[: self.k]]

        for i in range(self.k):
            pivot_row = i
            while pivot_row < self.k and matrix_c[pivot_row][i] == 0:
                pivot_row += 1
            if pivot_row >= self.k:
                return None
            if pivot_row != i:
                matrix_c[i], matrix_c[pivot_row] = matrix_c[pivot_row], matrix_c[i]
                matrix_v[i], matrix_v[pivot_row] = matrix_v[pivot_row], matrix_v[i]

            for j in range(i + 1, self.k):
                if matrix_c[j][i] != 0:
                    factor = matrix_c[j][i]
                    for c_idx in range(i, self.k):
                        matrix_c[j][c_idx] = (matrix_c[j][c_idx] - factor * matrix_c[i][c_idx]) % self.field_size
                    for b_idx in range(self.chunk_size):
                        matrix_v[j][b_idx] = (matrix_v[j][b_idx] - factor * matrix_v[i][b_idx]) % self.field_size

        decoded_chunks = [bytearray(self.chunk_size) for _ in range(self.k)]
        for i in range(self.k - 1, -1, -1):
            val = bytearray(matrix_v[i])
            for j in range(i + 1, self.k):
                factor = matrix_c[i][j]
                for b_idx in range(self.chunk_size):
                    val[b_idx] = (val[b_idx] - factor * decoded_chunks[j][b_idx]) % self.field_size
            decoded_chunks[i] = val

        raw_data = b"".join(bytes(c) for c in decoded_chunks)
        return raw_data.rstrip(b"\x00")
