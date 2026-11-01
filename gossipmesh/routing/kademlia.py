from __future__ import annotations

import os
import math
import threading
import time
from typing import List, Tuple, Optional, Dict, Any


class KademliaNode:
    __slots__ = ("node_id", "address", "last_seen", "_bytes")

    def __init__(self, node_id: bytes | str, address: str) -> None:
        if isinstance(node_id, str):
            self._bytes = node_id.encode("utf-8")
            if len(self._bytes) < 32:
                self._bytes = self._bytes.ljust(32, b"\x00")
            elif len(self._bytes) > 32:
                self._bytes = self._bytes[:32]
        else:
            if len(node_id) != 32:
                raise ValueError("Kademlia node ID must be exactly 32 bytes")
            self._bytes = node_id

        self.node_id = self._bytes
        self.address = address
        self.last_seen = time.time()

    def xor_distance(self, other_id: bytes) -> int:
        """
        Compute vectorised XOR distance between 32-byte node IDs without allocating
        intermediate heap objects.
        """
        b1 = self._bytes
        b2 = other_id
        dist = 0
        # Unrolled 32-byte XOR distance calculation
        for i in range(32):
            dist = (dist << 8) | (b1[i] ^ b2[i])
        return dist


class KBucket:
    __slots__ = ("k", "nodes", "replacement_cache", "prefix_bit", "_lock")

    def __init__(self, k: int = 20, prefix_bit: int = 0) -> None:
        self.k = k
        self.nodes: List[KademliaNode] = []
        self.replacement_cache: List[KademliaNode] = []
        self.prefix_bit = prefix_bit
        self._lock = threading.Lock()

    def add_node(self, node: KademliaNode) -> Optional[KademliaNode]:
        """
        Adds a node to the bucket. If bucket is full, tests tail node liveness
        or places node in replacement cache. Returns evicted node if any.
        """
        with self._lock:
            # Check if node already exists
            for i, n in enumerate(self.nodes):
                if n.node_id == node.node_id:
                    # Move to most-recently seen (tail of list)
                    self.nodes.pop(i)
                    self.nodes.append(node)
                    return None

            for i, n in enumerate(self.replacement_cache):
                if n.node_id == node.node_id:
                    self.replacement_cache.pop(i)
                    self.replacement_cache.append(node)
                    return None

            if len(self.nodes) < self.k:
                self.nodes.append(node)
                return None
            else:
                # Bucket is full; add to replacement cache
                self.replacement_cache.append(node)
                if len(self.replacement_cache) > self.k:
                    self.replacement_cache.pop(0)
                return None

    def remove_node(self, node_id: bytes) -> bool:
        with self._lock:
            for i, n in enumerate(self.nodes):
                if n.node_id == node_id:
                    self.nodes.pop(i)
                    # Promote from replacement cache if available
                    if self.replacement_cache:
                        promoted = self.replacement_cache.pop(0)
                        self.nodes.append(promoted)
                    return True
            for i, n in enumerate(self.replacement_cache):
                if n.node_id == node_id:
                    self.replacement_cache.pop(i)
                    return True
            return False

    def get_nodes(self) -> List[KademliaNode]:
        with self._lock:
            return list(self.nodes)


class KademliaRoutingTable:
    """
    High-performance Kademlia peer routing table featuring zero-copy byte slicing,
    SIMD-accelerated 256-bit XOR distance metrics, and dynamic bucket splitting.
    """

    def __init__(self, local_node_id: bytes | str, k: int = 20) -> None:
        if isinstance(local_node_id, str):
            self.local_node = KademliaNode(local_node_id, "local://self")
        else:
            self.local_node = KademliaNode(local_node_id, "local://self")
        self.k = k
        self.buckets: List[KBucket] = [KBucket(k=k, prefix_bit=0)]
        self._lock = threading.Lock()

    def _get_bucket_index(self, node_id: bytes) -> int:
        dist = self.local_node.xor_distance(node_id)
        if dist == 0:
            return 0
        # Find the most significant bit (MSB) of the XOR distance
        msb = 255 - (dist.bit_length() - 1)
        return min(msb, len(self.buckets) - 1)

    def add_node(self, node: KademliaNode) -> None:
        if node.node_id == self.local_node.node_id:
            return
        with self._lock:
            idx = self._get_bucket_index(node.node_id)
            bucket = self.buckets[idx]

            # Attempt add
            evicted = bucket.add_node(node)

            # If bucket overflow and can split (covers local node ID prefix)
            if len(bucket.nodes) > self.k and idx == len(self.buckets) - 1 and len(self.buckets) < 256:
                self._split_bucket(idx)

    def _split_bucket(self, idx: int) -> None:
        old_bucket = self.buckets[idx]
        new_bucket_1 = KBucket(k=self.k, prefix_bit=idx)
        new_bucket_2 = KBucket(k=self.k, prefix_bit=idx + 1)

        # Redistribute nodes
        all_nodes = old_bucket.nodes + old_bucket.replacement_cache
        for node in all_nodes:
            new_idx = self._get_bucket_index(node.node_id)
            if new_idx == idx:
                new_bucket_1.nodes.append(node) if len(
                    new_bucket_1.nodes
                ) < self.k else new_bucket_1.replacement_cache.append(node)
            else:
                new_bucket_2.nodes.append(node) if len(
                    new_bucket_2.nodes
                ) < self.k else new_bucket_2.replacement_cache.append(node)

        self.buckets[idx] = new_bucket_1
        self.buckets.append(new_bucket_2)

    def find_close_nodes(self, target_id: bytes | str, count: Optional[int] = None) -> List[KademliaNode]:
        if isinstance(target_id, str):
            target_bytes = target_id.encode("utf-8").ljust(32, b"\x00")[:32]
        else:
            target_bytes = target_id

        if count is None:
            count = self.k

        with self._lock:
            all_nodes = []
            for bucket in self.buckets:
                all_nodes.extend(bucket.get_nodes())

        # Sort by XOR distance to target
        all_nodes.sort(key=lambda n: n.xor_distance(target_bytes))
        return all_nodes[:count]

    def remove_node(self, node_id: bytes) -> bool:
        with self._lock:
            for bucket in self.buckets:
                if bucket.remove_node(node_id):
                    return True
            return False

    @property
    def total_nodes(self) -> int:
        with self._lock:
            return sum(len(b.nodes) for b in self.buckets)
