import hashlib
import time
import asyncio
from typing import List, Dict, Optional, Tuple, Any


class KademliaNode:
    def __init__(self, node_id: str, address: str, port: int, last_seen: Optional[float] = None):
        self.node_id = node_id
        self.address = address
        self.port = port
        self.last_seen = last_seen or time.time()

    @property
    def integer_id(self) -> int:
        return int(self.node_id, 16)

    def update_seen(self):
        self.last_seen = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {"node_id": self.node_id, "address": self.address, "port": self.port, "last_seen": self.last_seen}


class KademliaBucket:
    def __init__(self, k: int = 20):
        self.k = k
        self.nodes: List[KademliaNode] = []

    def add_node(self, node: KademliaNode):
        for i, existing in enumerate(self.nodes):
            if existing.node_id == node.node_id:
                self.nodes.pop(i)
                self.nodes.append(node)
                return
        if len(self.nodes) < self.k:
            self.nodes.append(node)
        else:
            # Bucket is full; implement LRU eviction check on oldest
            oldest = self.nodes[0]
            # For a basic robust DHT, we can drop or replace if unresponsive.
            # Here we keep simple tail drop / replacement for stale nodes.
            self.nodes.pop(0)
            self.nodes.append(node)

    def remove_node(self, node_id: str):
        self.nodes = [n for n in self.nodes if n.node_id != node_id]


class KademliaDHT:
    def __init__(self, local_node_id: str, k: int = 20, alpha: int = 3):
        self.local_node_id = local_node_id
        self.local_int_id = int(local_node_id, 16)
        self.k = k
        self.alpha = alpha
        # 160 bits for SHA-1 / 256 bits for SHA-256 space
        self.buckets: List[KademliaBucket] = [KademliaBucket(k) for _ in range(256)]
        self.storage: Dict[str, str] = {}

    def _get_bucket_index(self, target_id: str) -> int:
        target_int = int(target_id, 16)
        distance = self.local_int_id ^ target_int
        if distance == 0:
            return 0
        return distance.bit_length() - 1

    def add_node(self, node: KademliaNode):
        if node.node_id == self.local_node_id:
            return
        idx = self._get_bucket_index(node.node_id)
        if 0 <= idx < len(self.buckets):
            self.buckets[idx].add_node(node)

    def find_close_nodes(self, target_id: str, count: int = 20) -> List[KademliaNode]:
        target_int = int(target_id, 16)
        all_nodes = []
        for bucket in self.buckets:
            all_nodes.extend(bucket.nodes)

        # Sort by XOR distance
        all_nodes.sort(key=lambda n: n.integer_id ^ target_int)
        return all_nodes[:count]

    def store(self, key: str, value: str):
        self.storage[key] = value

    def get(self, key: str) -> Optional[str]:
        return self.storage.get(key)
