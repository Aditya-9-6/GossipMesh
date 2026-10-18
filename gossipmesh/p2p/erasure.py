import math
from typing import List, Tuple, Optional

class GaloisField:
    """GF(2^8) arithmetic using carryless multiplication and log/antilog tables."""
    def __init__(self, prim: int = 0x11d):
        self.exp = [0] * 512
        self.log = [0] * 256
        x = 1
        for i in range(255):
            self.exp[i] = x
            self.exp[i + 255] = x
            self.log[x] = i
            x <<= 1
            if x & 0x100:
                x ^= prim
        self.log[0] = 0  # undefined, but safe fallback

    def add(self, a: int, b: int) -> int:
        return a ^ b

    def sub(self, a: int, b: int) -> int:
        return a ^ b

    def mul(self, a: int, b: int) -> int:
        if a == 0 or b == 0:
            return 0
        return self.exp[self.log[a] + self.log[b]]

    def div(self, a: int, b: int) -> int:
        if a == 0:
            return 0
        if b == 0:
            raise ZeroDivisionError("Division by zero in GF(2^8)")
        return self.exp[(self.log[a] - self.log[b]) % 255]

    def inverse(self, a: int) -> int:
        return self.div(1, a)


GF = GaloisField()


class ErasureCoder:
    """Reed-Solomon style fragment multiplexer for GossipMesh P2P payloads
    using true Vandermonde matrix inversion over GF(2^8).
    """
    def __init__(self, k: int = 4, m: int = 2):
        self.k = k
        self.m = m
        total = k + m
        if total > 256:
            raise ValueError("Total shards (k + m) cannot exceed 256 for byte fields.")

    def _vandermonde_matrix(self, rows: int, cols: int) -> List[List[int]]:
        matrix = []
        for i in range(rows):
            row = []
            for j in range(cols):
                # Standard Vandermonde element: (i+1)^j in GF(2^8)
                base = i + 1
                val = 1
                for _ in range(j):
                    val = GF.mul(val, base)
                row.append(val)
            matrix.append(row)
        return matrix

    def encode(self, payload: bytes) -> List[Tuple[int, bytes]]:
        """Encodes a byte payload into k + m fragments.
        Returns a list of tuples: (shard_index, shard_data).
        """
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
            
        # Generate Vandermonde encoding matrix for parity rows
        # Identity top k x k, Vandermonde bottom m x k
        v_matrix = self._vandermonde_matrix(self.m, self.k)
        
        parity_shards = []
        for j in range(self.m):
            parity_chunk = bytearray(chunk_size)
            row = v_matrix[j]
            for b_idx in range(chunk_size):
                acc = 0
                for i in range(self.k):
                    val = shards[i][b_idx]
                    acc ^= GF.mul(val, row[i])
                parity_chunk[b_idx] = acc
            parity_shards.append(bytes(parity_chunk))
            
        all_fragments = []
        for i, shard in enumerate(shards):
            all_fragments.append((i, shard))
        for j, p_shard in enumerate(parity_shards):
            all_fragments.append((self.k + j, p_shard))
            
        return all_fragments

    def decode(self, fragments: List[Tuple[int, bytes]], original_size: Optional[int] = None) -> bytes:
        """Reconstructs the original payload from any k fragments out of k + m
        using matrix inversion over GF(2^8).
        """
        if len(fragments) < self.k:
            raise ValueError(f"Insufficient fragments for reconstruction: got {len(fragments)}, need {self.k}")
            
        # Sort and pick first k fragments
        sorted_frags = sorted(fragments, key=lambda x: x[0])[:self.k]
        chunk_size = len(sorted_frags[0][1])
        
        indices = [idx for idx, _ in sorted_frags]
        
        # Check if all data shards are already present
        if all(idx < self.k for idx in indices):
            reconstructed_chunks = [data for _, data in sorted_frags]
            combined = b''.join(reconstructed_chunks)
            if original_size is not None:
                return combined[:original_size]
            return combined.rstrip(b'\x00')
            
        # Build submatrix corresponding to available fragments
        full_v = self._vandermonde_matrix(self.k, self.k) # Using identity + vandermonde mapping
        sub_matrix = []
        for idx in indices:
            if idx < self.k:
                # Identity row
                row = [0] * self.k
                row[idx] = 1
                sub_matrix.append(row)
            else:
                # Parity row from Vandermonde
                p_idx = idx - self.k
                v_full = self._vandermonde_matrix(self.m, self.k)
                sub_matrix.append(v_full[p_idx])

        # Invert sub_matrix using Gauss-Jordan elimination in GF(2^8)
        inv_matrix = self._invert_matrix(sub_matrix)
        
        # Reconstruct original k shards
        reconstructed_shards = [bytearray(chunk_size) for _ in range(self.k)]
        for b_idx in range(chunk_size):
            for i in range(self.k):
                acc = 0
                inv_row = inv_matrix[i]
                for j, (_, data) in enumerate(sorted_frags):
                    acc ^= GF.mul(inv_row[j], data[b_idx])
                reconstructed_shards[i][b_idx] = acc
                
        combined = b''.join(bytes(s) for s in reconstructed_shards)
        if original_size is not None:
            return combined[:original_size]
        return combined.rstrip(b'\x00')

    def _invert_matrix(self, matrix: List[List[int]]) -> List[List[int]]:
        n = len(matrix)
        # Augment with identity matrix
        aug = [row[:] + [1 if i == j else 0 for j in range(n)] for i, row in enumerate(matrix)]

        for i in range(n):
            # Pivot
            pivot = aug[i][i]
            if pivot == 0:
                # Find non-zero pivot below
                found = False
                for r in range(i + 1, n):
                    if aug[r][i] != 0:
                        aug[i], aug[r] = aug[r], aug[i]
                        pivot = aug[i][i]
                        found = True
                        break
                if not found:
                    raise ValueError("Matrix is singular and cannot be inverted in GF(2^8)")

            inv_pivot = GF.inverse(pivot)
            for j in range(2 * n):
                aug[i][j] = GF.mul(aug[i][j], inv_pivot)

            for r in range(n):
                if r != i:
                    factor = aug[r][i]
                    if factor != 0:
                        for j in range(2 * n):
                            aug[r][j] = GF.sub(aug[r][j], GF.mul(factor, aug[i][j]))

        # Extract inverse from right half
        return [row[n:] for row in aug]
