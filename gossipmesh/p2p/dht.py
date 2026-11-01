"""
Distributed Hash Table (DHT) implementation for GossipMesh P2P topology.
"""

import threading
from typing import Dict, List, Optional, Tuple, Any


def id_to_int(node_id: str) -> int:
    return int(node_id, 16)


def xor_distance(id1: str, id2: str) -> int:
    return id_to_int(id1) ^ id_to_int(id2)


class KademliaNode:
    def __init__(self, node_id: str, address: str, port: int):
        self.node_id = node_id
        self.address = address
        self.port = port


class KBucket:
    def __init__(self, k: int = 20):
        self.k = k
        self.nodes: List[KademliaNode] = []
        self._lock = threading.Lock()

    def add_node(self, node: KademliaNode) -> bool:
        with self._lock:
            for existing in self.nodes:
                if existing.node_id == node.node_id:
                    self.nodes.remove(existing)
                    self.nodes.append(node)
                    return True
            if len(self.nodes) < self.k:
                self.nodes.append(node)
                return True
            return False

    def remove(self, node_id: str) -> None:
        with self._lock:
            self.nodes = [n for n in self.nodes if n.node_id != node_id]


class KademliaDHT:
    def __init__(self, node_id: str, bit_length: int = 160, k: int = 20):
        self.node_id = node_id
        self.bit_length = bit_length
        self.buckets: List[KBucket] = [KBucket(k) for _ in range(bit_length)]
        self.storage: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def _bucket_index(self, node_id: str) -> int:
        dist = xor_distance(self.node_id, node_id)
        if dist == 0:
            return 0
        index = dist.bit_length() - 1
        return max(0, min(index, self.bit_length - 1))

    def add_node(self, node_or_id: Any, address: Optional[str] = None, port: Optional[int] = None) -> bool:
        if isinstance(node_or_id, KademliaNode):
            node_id = node_or_id.node_id
            node = node_or_id
        else:
            node_id = node_or_id
            assert address is not None and port is not None
            node = KademliaNode(node_id, address, port)
        index = self._bucket_index(node_id)
        return self.buckets[index].add_node(node)

    def remove_node(self, node_id: str) -> None:
        index = self._bucket_index(node_id)
        with self._lock:
            self.buckets[index].remove(node_id)

    def find_close_nodes(self, target_id: str, count: int = 20) -> List[Any]:
        all_contacts: List[Tuple[str, str, int]] = []
        with self._lock:
            for bucket in self.buckets:
                for node in bucket.nodes:
                    dist = xor_distance(node.node_id, target_id)
                    all_contacts.append((node.node_id, node.address, dist))
        all_contacts.sort(key=lambda x: x[2])
        return all_contacts[:count]

    def store(self, key: str, value: Any) -> None:
        with self._lock:
            self.storage[key] = value

    def get(self, key: str) -> Any:
        with self._lock:
            return self.storage.get(key)
