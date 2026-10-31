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
    """Represents a peer node in the Kademlia DHT."""

    def __init__(self, node_id: str, address: str, port: int) -> None:
        self.node_id = node_id
        self.address = address
        self.port = port


class KBucket:
    """A k-bucket holding up to k contacts, ordered by last seen (LRU policy)."""

    def __init__(self, k: int = 20) -> None:
        self.k = k
        self.contacts: List[Tuple[str, str]] = []  # List of (node_id, address)
        self._lock = threading.Lock()

    def update(self, node_id: str, address: str) -> bool:
        """Update or add a contact in the k-bucket. Returns True if added/updated."""
        with self._lock:
            for i, (nid, _) in enumerate(self.contacts):
                if nid == node_id:
                    self.contacts.pop(i)
                    self.contacts.append((node_id, address))
                    return True

            if len(self.contacts) < self.k:
                self.contacts.append((node_id, address))
                return True
            return False

    def remove(self, node_id: str) -> None:
        with self._lock:
            self.contacts = [(nid, addr) for nid, addr in self.contacts if nid != node_id]

    def get_contacts(self) -> List[Tuple[str, str]]:
        with self._lock:
            return list(self.contacts)


class KademliaDHT:
    """Kademlia DHT routing table managing multiple k-buckets and key-value storage."""

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

    def add_node(self, node_or_id: Any, address: Optional[str] = None, port: Optional[int] = None) -> bool:
        if isinstance(node_or_id, KademliaNode):
            node_id = node_or_id.node_id
            addr = f"{node_or_id.address}:{node_or_id.port}"
        else:
            node_id = node_or_id
            addr = address or "127.0.0.1"

        if node_id == self.local_node_id:
            return False
        index = self._bucket_index(node_id)
        with self._lock:
            return self.buckets[index].update(node_id, addr)

    def remove_node(self, node_id: str) -> None:
        index = self._bucket_index(node_id)
        with self._lock:
            self.buckets[index].remove(node_id)

    def find_close_nodes(self, target_id: str, count: int = 20) -> List[Any]:
        """Find the closest nodes to the target ID ordered by XOR distance."""
        all_contacts: List[Tuple[str, str]] = []
        with self._lock:
            for bucket in self.buckets:
                all_contacts.extend(bucket.get_contacts())

        seen = set()
        unique_contacts = []
        for nid, addr in all_contacts:
            if nid not in seen and nid != self.local_node_id:
                seen.add(nid)
                parts = addr.split(":")
                ip = parts[0]
                port = int(parts[1]) if len(parts) > 1 else 9000
                unique_contacts.append(KademliaNode(node_id=nid, address=ip, port=port))

        unique_contacts.sort(key=lambda item: xor_distance(item.node_id, target_id))
        return unique_contacts[:count]

    def store(self, key: str, value: Any) -> None:
        with self._lock:
            self._storage[key] = value

    def get(self, key: str) -> Any:
        with self._lock:
            return self._storage.get(key)
