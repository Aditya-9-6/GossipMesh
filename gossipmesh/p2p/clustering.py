from __future__ import annotations

import threading
from typing import Dict, List, Tuple, Optional
import numpy as np

from gossipmesh.p2p.minhash import MinHashSketch


class PeerTopologyClustering:
    """
    Clusters peer nodes in distributed gossip meshes using zero-copy MinHash sketches
    and threshold-based Jaccard similarity bounds without full payload exchange.
    """

    def __init__(self, similarity_threshold: float = 0.5, num_perm: int = 128) -> None:
        self.similarity_threshold = similarity_threshold
        self.num_perm = num_perm
        self._sketches: Dict[str, MinHashSketch] = {}
        self._lock = threading.Lock()

    def register_peer(self, peer_id: str, sketch: MinHashSketch) -> None:
        with self._lock:
            self._sketches[peer_id] = sketch

    def remove_peer(self, peer_id: str) -> None:
        with self._lock:
            self._sketches.pop(peer_id, None)

    def compute_similarity(self, peer_a: str, peer_b: str) -> float:
        with self._lock:
            if peer_a not in self._sketches or peer_b not in self._sketches:
                raise KeyError(f"One or both peers not found in clustering registry: {peer_a}, {peer_b}")
            return self._sketches[peer_a].jaccard(self._sketches[peer_b])

    def cluster_peers(self) -> List[List[str]]:
        """
        Groups peers into connected component clusters based on Jaccard similarity threshold.
        Concurrency safe and zero-allocation friendly.
        """
        with self._lock:
            peers = list(self._sketches.keys())
            n = len(peers)
            if n == 0:
                return []

            parent = list(range(n))

            def find(i: int) -> int:
                root = i
                while root != parent[root]:
                    root = parent[root]
                curr = i
                while curr != root:
                    nxt = parent[curr]
                    parent[curr] = root
                    curr = nxt
                return root

            def union(i: int, j: int) -> None:
                root_i = find(i)
                root_j = find(j)
                if root_i != root_j:
                    parent[root_i] = root_j

            sketches = [self._sketches[p] for p in peers]

            # Compare all pairs (approximate clustering)
            for i in range(n):
                for j in range(i + 1, n):
                    sim = sketches[i].jaccard(sketches[j])
                    if sim >= self.similarity_threshold:
                        union(i, j)

            clusters_map: Dict[int, List[str]] = {}
            for i, peer_id in enumerate(peers):
                root = find(i)
                if root not in clusters_map:
                    clusters_map[root] = []
                clusters_map[root].append(peer_id)

            return list(clusters_map.values())

    def find_nearest_cluster_centroid(self, query_sketch: MinHashSketch) -> Tuple[Optional[str], float]:
        """Finds the peer with the highest Jaccard similarity to the query sketch."""
        with self._lock:
            best_peer = None
            max_sim = -1.0
            for peer_id, sketch in self._sketches.items():
                try:
                    sim = query_sketch.jaccard(sketch)
                    if sim > max_sim:
                        max_sim = sim
                        best_peer = peer_id
                except Exception:
                    continue
            return best_peer, max_sim
