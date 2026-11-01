from __future__ import annotations

import threading
from typing import Dict, List, Tuple, Optional
from gossipmesh.p2p.minhash import MinHashSketch


class MinHashSketchRegistry:
    """
    Thread-safe registry for managing peer MinHash sketches and conducting
    sub-millisecond distributed topology deduplication and similarity routing.
    """

    def __init__(self, num_perm: int = 128, max_capacity: int = 10000, similarity_threshold: float = 0.85):
        self.num_perm = num_perm
        self.max_capacity = max_capacity
        self.similarity_threshold = similarity_threshold
        self._sketches: Dict[str, MinHashSketch] = {}
        self._lock = threading.RLock()

    def register_peer(self, peer_id: str, tokens: Optional[List[str]] = None) -> MinHashSketch:
        """Register or update a peer sketch in the registry."""
        with self._lock:
            if peer_id in self._sketches:
                sketch = self._sketches[peer_id]
            else:
                if len(self._sketches) >= self.max_capacity:
                    self._enforce_memory_pressure_downsampling()
                sketch = MinHashSketch(num_perm=self.num_perm)
                self._sketches[peer_id] = sketch

            if tokens:
                sketch.update_batch(tokens)
            return sketch

    def get_sketch(self, peer_id: str) -> Optional[MinHashSketch]:
        with self._lock:
            return self._sketches.get(peer_id)

    def remove_peer(self, peer_id: str) -> bool:
        with self._lock:
            if peer_id in self._sketches:
                del self._sketches[peer_id]
                return True
            return False

    def find_duplicates(self, peer_id: str) -> List[Tuple[str, float]]:
        """
        Find active peers whose routing tables exceed the similarity threshold
        for topology deduplication.
        """
        with self._lock:
            target_sketch = self._sketches.get(peer_id)
            if not target_sketch:
                return []

            duplicates = []
            for other_id, sketch in self._sketches.items():
                if other_id == peer_id:
                    continue
                sim = target_sketch.jaccard(sketch)
                if sim >= self.similarity_threshold:
                    duplicates.append((other_id, sim))
            return duplicates

    def _enforce_memory_pressure_downsampling(self) -> None:
        """Dynamically downsample existing neighborhood sets under memory pressure."""
        new_perm = max(32, self.num_perm // 2)
        downsampled: Dict[str, MinHashSketch] = {}
        for pid, sketch in self._sketches.items():
            downsampled[pid] = sketch.downsample(new_perm)
        self.num_perm = new_perm
        self._sketches = downsampled

    def size(self) -> int:
        with self._lock:
            return len(self._sketches)
