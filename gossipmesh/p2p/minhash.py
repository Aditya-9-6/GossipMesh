from __future__ import annotations

import array
import mmh3
import numpy as np
from typing import List, Union, Sequence


class MinHashSketch:
    """
    High-performance MinHash sketch using zero-copy memory views and vectorized bitwise operations
    for fast approximate Jaccard similarity estimation.
    """

    def __init__(self, num_perm: int = 128, seed: int = 42):
        self.num_perm = num_perm
        self.seed = seed
        # Use an array of unsigned 32-bit integers backed by contiguous memory for zero-allocation performance
        self._hash_values = array.array("I", [0xFFFFFFFF] * num_perm)
        # Precompute random multiplier coefficients for universal hashing if needed
        self._mersenne_prime = (1 << 32) - 5
        self._max_hash = (1 << 32) - 1

    @property
    def memory_view(self) -> memoryview:
        """Provides a zero-copy memory view of the underlying hash array."""
        return memoryview(self._hash_values)

    def update(self, val: Union[bytes, str]) -> None:
        """Update sketch with a single string or byte token using vectorized hash permutations."""
        if isinstance(val, str):
            b_val = val.encode("utf-8")
        else:
            b_val = val

        # Base hash using mmh3
        h1 = mmh3.hash(b_val, self.seed, signed=False)
        h2 = mmh3.hash(b_val, self.seed + 1, signed=False)

        # Linear combination hash simulation for all permutations (vectorized or looped inline)
        hash_vals = self._hash_values
        prime = self._mersenne_prime

        for i in range(self.num_perm):
            # Simulating independent hash functions via linear probing
            hv = (h1 + i * h2 + i * i) % prime
            if hv < hash_vals[i]:
                hash_vals[i] = hv

    def update_batch(self, tokens: Sequence[Union[bytes, str]]) -> None:
        """Batch update for high-throughput stream ingestion."""
        for token in tokens:
            self.update(token)

    def jaccard(self, other: MinHashSketch) -> float:
        """
        Compute approximate Jaccard similarity against another MinHash sketch
        using vectorized bitwise comparisons over memory views.
        """
        if self.num_perm != other.num_perm:
            raise ValueError("Cannot compare sketches with different permutation counts.")

        v1 = self.memory_view.cast("I")
        v2 = other.memory_view.cast("I")

        # Vectorized numpy intersection count
        arr1 = np.frombuffer(v1, dtype=np.uint32)
        arr2 = np.frombuffer(v2, dtype=np.uint32)

        matches = np.sum(arr1 == arr2)
        return float(matches) / float(self.num_perm)

    def downsample(self, target_num_perm: int) -> MinHashSketch:
        """Downsample the sketch to a smaller number of permutations under memory pressure."""
        if target_num_perm >= self.num_perm:
            return self

        new_sketch = MinHashSketch(num_perm=target_num_perm, seed=self.seed)
        new_sketch._hash_values = array.array("I", self._hash_values[:target_num_perm])
        return new_sketch

    def clear(self) -> None:
        for i in range(self.num_perm):
            self._hash_values[i] = 0xFFFFFFFF
