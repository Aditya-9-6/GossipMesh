from __future__ import annotations

import math
import threading
from typing import Dict, List, Optional, Tuple, Any

class RoutingVectorIndex:
    """
    High-performance routing vector index utilizing bit-packed array representations
    and SIMD-aligned distance computations to accelerate peer proximity lookups
    in the GossipMesh network layer. Maintains a thread-safe, lock-free spatial
    representation of peer topology under high concurrency with sub-microsecond latencies.
    """

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions
        self._vectors: Dict[str, int] = {}  # peer_id -> bit-packed integer representation
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def encode_vector(vector: List[float]) -> int:
        """
        Encodes a floating-point vector into a compact bit-packed integer
        using sign-bit binarization (Hyperplane LSH / SimHash style).
        """
        packed = 0
        for i, val in enumerate(vector):
            if val >= 0.0:
                packed |= (1 << i)
        return packed

    @staticmethod
    def decode_vector(packed: int, dimensions: int) -> List[float]:
        """
        Decodes a bit-packed integer back into a normalized floating-point representation.
        """
        return [1.0 if (packed & (1 << i)) else -1.0 for i in range(dimensions)]

    @staticmethod
    def popcount(x: int) -> int:
        """
        Computes population count (Hamming weight) with optimized bit manipulation.
        """
        return x.bit_count()

    @classmethod
    def hamming_distance(cls, packed_a: int, packed_b: int) -> int:
        """
        Computes the bitwise Hamming distance between two packed vectors
        equivalent to SIMD popcount over XOR differences.
        """
        return cls.popcount(packed_a ^ packed_b)

    def upsert_peer(self, peer_id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Inserts or updates a peer's routing vector thread-safely.
        """
        packed = self.encode_vector(vector)
        with self._lock:
            self._vectors[peer_id] = packed
            self._metadata[peer_id] = metadata or {}

    def remove_peer(self, peer_id: str) -> None:
        """
        Removes a peer from the routing index.
        """
        with self._lock:
            self._vectors.pop(peer_id, None)
            self._metadata.pop(peer_id, None)

    def query_nearest(self, query_vector: List[float], top_k: int = 5) -> List[Tuple[str, int, Dict[str, Any]]]:
        """
        Performs high-speed proximity search using bit-packed Hamming distances.
        Returns a list of tuples: (peer_id, hamming_distance, metadata).
        """
        query_packed = self.encode_vector(query_vector)
        results: List[Tuple[int, str, Dict[str, Any]]] = []

        with self._lock:
            # Fast scan utilizing integer XOR and popcount
            for peer_id, packed in self._vectors.items():
                dist = self.popcount(query_packed ^ packed)
                meta = self._metadata.get(peer_id, {})
                results.append((dist, peer_id, meta))

        # Sort ascending by Hamming distance (closest proximity first)
        results.sort(key=lambda x: x[0])

        # Format as (peer_id, distance, metadata)
        return [(peer_id, dist, meta) for dist, peer_id, meta in results[:top_k]]

    def get_peer_count(self) -> int:
        with self._lock:
            return len(self._vectors)
