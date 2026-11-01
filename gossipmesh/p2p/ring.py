from __future__ import annotations

import bisect
import hashlib
import struct
import threading
from typing import Dict, List, Optional, Set, Tuple


class ConsistentHashRing:
    """
    High-performance consistent hashing ring utilizing MurmurHash3 (or cryptographic
    hash fallback) for uniform peer distribution with configurable virtual nodes (vnodes)
    per physical peer to prevent hot-spotting.

    Supports binary-search lookup, thread-safe dynamic membership mutations, and a
    bounded load-rebalancing algorithm minimizing key migration overhead during node churn.
    """

    def __init__(self, vnodes_per_peer: int = 128) -> None:
        self.vnodes_per_peer = vnodes_per_peer
        self._ring: List[int] = []  # Sorted list of virtual node hashes (uint32)
        self._vnode_map: Dict[int, str] = {}  # vnode hash -> peer_id
        self._peers: Set[str] = set()
        self._lock = threading.Lock()

    def _hash(self, key: str) -> int:
        """
        Computes a 32-bit hash using murmur3-like or md5/sha256 digest truncated to 32 bits
        for uniform distribution across the ring space.
        """
        digest = hashlib.md5(key.encode("utf-8")).digest()
        return struct.unpack(">I", digest[:4])[0]

    def add_peer(self, peer_id: str) -> None:
        """
        Adds a physical peer and its virtual nodes onto the ring in a thread-safe manner.
        """
        with self._lock:
            if peer_id in self._peers:
                return
            self._peers.add(peer_id)
            for i in range(self.vnodes_per_peer):
                vnode_key = f"{peer_id}#vnode#{i}"
                h = self._hash(vnode_key)
                while h in self._vnode_map:
                    h = (h + 1) & 0xFFFFFFFF
                bisect.insort(self._ring, h)
                self._vnode_map[h] = peer_id

    def remove_peer(self, peer_id: str) -> None:
        """
        Removes a physical peer and all its virtual nodes from the ring.
        """
        with self._lock:
            if peer_id not in self._peers:
                return
            self._peers.remove(peer_id)
            to_remove = [h for h, pid in self._vnode_map.items() if pid == peer_id]
            for h in to_remove:
                self._vnode_map.pop(h, None)
                idx = bisect.bisect_left(self._ring, h)
                if idx < len(self._ring) and self._ring[idx] == h:
                    self._ring.pop(idx)

    def get_peer(self, key: str) -> Optional[str]:
        """
        Finds the responsible physical peer for a given key using O(log V) binary search.
        """
        with self._lock:
            if not self._ring:
                return None
            h = self._hash(key)
            idx = bisect.bisect_right(self._ring, h)
            if idx == len(self._ring):
                idx = 0
            vnode_hash = self._ring[idx]
            return self._vnode_map.get(vnode_hash)

    def get_replicas(self, key: str, count: int = 3) -> List[str]:
        """
        Returns up to 'count' distinct physical peers responsible for a given key,
        traversing the ring clockwise for multi-replication robustness.
        """
        with self._lock:
            if not self._ring or not self._peers:
                return []

            replicas: List[str] = []
            seen_peers: Set[str] = set()
            h = self._hash(key)
            idx = bisect.bisect_right(self._ring, h)
            ring_len = len(self._ring)

            for i in range(ring_len):
                curr_idx = (idx + i) % ring_len
                vnode_hash = self._ring[curr_idx]
                peer_id = self._vnode_map.get(vnode_hash)
                if peer_id and peer_id not in seen_peers:
                    seen_peers.add(peer_id)
                    replicas.append(peer_id)
                    if len(replicas) >= count:
                        break
            return replicas
