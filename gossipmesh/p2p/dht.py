"""Kademlia Distributed Hash Table (DHT) for Peer Discovery. Implements XOR metric routing, k-buckets, and active peer management."""

import hashlib
import threading
from typing import Dict, List, Optional, Tuple, Any


def id_to_int(node_id: str) -> int:
    """Convert a hex string or arbitrary string ID into an integer for XOR metric calculation."""
    if len(node_id) == 40 and all(c in "0123456789abcdefABCDEF" for c in node_id):
        return int(node_id, 16)
    digest = hashlib.sha1(node_id.encode("utf-8")).hexdigest()
    return int(digest, 16)


def xor_distance(id1: str, id2: str) -> int:
    """Calculate the XOR distance between two node IDs."""
    return id_to_int(id1) ^ id_to_int(id2)


class KademliaNode:
    def __init__(self, node_id: str, address: str, port: int, last_seen: Optional[float] = None):
        self.node_id = node_id
        self.address = address
        self.port = port
        self.last_seen = last_seen or 0.0

    @property
    def integer_id(self) -> int:
        return id_to_int(self.node_id)

    def update_seen(self):
        import time

        self.last_seen = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {"node_id": self.node_id, "address": self.address, "port": self.port, "last_seen": self.last_seen}


class KBucket:
    """A k-bucket holding up to k contacts, ordered by last seen (LRU policy)."""

    def __init__(self, k: int = 20) -> None:
        self.k = k
        self.contacts: List[KademliaNode] = []
        self._lock = threading.Lock()

    def update(self, node: KademliaNode) -> bool:
        """Update or add a contact in the k-bucket. Returns True if added/updated."""
        with self._lock:
            for i, existing in enumerate(self.contacts):
                if existing.node_id == node.node_id:
                    self.contacts.pop(i)
                    self.contacts.append(node)
                    return True
            if len(self.contacts) < self.k:
                self.contacts.append(node)
                return True
            return False

    def remove(self, node_id: str) -> None:
        with self._lock:
            self.contacts = [n for n in self.contacts if n.node_id != node_id]

    def get_contacts(self) -> List[KademliaNode]:
        with self._lock:
            return list(self.contacts)


class KademliaDHT:
    """Kademlia DHT routing table managing multiple k-buckets."""

    def __init__(self, local_node_id: str, k: int = 20, bit_length: int = 160) -> None:
        self.local_node_id = local_node_id
        self.k = k
        self.bit_length = bit_length
        self.buckets: List[KBucket] = [KBucket(k) for _ in range(bit_length)]
        self._storage: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def _bucket_index(self, node_id: str) -> int:
        dist = xor_distance(self.local_node_id, node_id)
        if dist == 0:
            return 0
        index = self.bit_length - dist.bit_length()
        return max(0, min(index, self.bit_length - 1))

    def add_node(self, node: KademliaNode) -> bool:
        if node.node_id == self.local_node_id:
            return False
        index = self._bucket_index(node.node_id)
        with self._lock:
            return self.buckets[index].update(node)

    def remove_node(self, node_id: str) -> None:
        index = self._bucket_index(node_id)
        with self._lock:
            self.buckets[index].remove(node_id)

    def find_close_nodes(self, target_id: str, count: int = 20) -> List[KademliaNode]:
        """Find the closest nodes to the target ID ordered by XOR distance."""
        all_contacts: List[KademliaNode] = []
        with self._lock:
            for bucket in self.buckets:
                all_contacts.extend(bucket.get_contacts())

        seen = set()
        unique_contacts = []
        for node in all_contacts:
            if node.node_id not in seen and node.node_id != self.local_node_id:
                seen.add(node.node_id)
                unique_contacts.append(node)

        unique_contacts.sort(key=lambda n: xor_distance(n.node_id, target_id))
        return unique_contacts[:count]

    def store(self, key: str, value: Any) -> None:
        with self._lock:
            self._storage[key] = value

    def get(self, key: str) -> Any:
        with self._lock:
            return self._storage.get(key)
