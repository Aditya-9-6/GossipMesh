"""Kademlia Distributed Hash Table (DHT) for Peer Discovery. Implements XOR metric routing, k-buckets, and active peer management."""

import hashlib
import threading
from typing import Dict, List, Optional, Tuple


class KademliaNode:
    def __init__(self, node_id: str, address: str, port: int):
        self.node_id = node_id
        self.address = address
        self.port = port


def id_to_int(node_id: str) -> int:
    """Convert a hex string or arbitrary string ID into an integer for XOR metric calculation."""
    if len(node_id) == 40 and all(c in "0123456789abcdefABCDEF" for c in node_id):
        return int(node_id, 16)
    digest = hashlib.sha1(node_id.encode("utf-8")).hexdigest()
    return int(digest, 16)


def xor_distance(id1: str, id2: str) -> int:
    """Calculate the XOR distance between two node IDs."""
    return id_to_int(id1) ^ id_to_int(id2)


class KBucket:
    """A k-bucket holding up to k contacts, ordered by last seen (LRU policy)."""

    def __init__(self, k: int = 20) -> None:
        self.k = k
        self.contacts: List[Tuple[str, str]] = []
        self._lock = threading.Lock()

    def update(self, node_id: str, address: str) -> bool:
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
    """Kademlia DHT routing table managing multiple k-buckets."""

    def __init__(self, local_node_id: str, k: int = 20, bit_length: int = 160) -> None:
        self.local_node_id = local_node_id
        self.k = k
        self.bit_length = bit_length
        self.buckets: List[KBucket] = [KBucket(k) for _ in range(bit_length)]
        self._lock = threading.Lock()
        self.storage: Dict[str, Any] = {}

    def _bucket_index(self, node_id: str) -> int:
        dist = xor_distance(self.local_node_id, node_id)
        if dist == 0:
            return 0
        index = self.bit_length - dist.bit_length()
        return max(0, min(index, self.bit_length - 1))

    def add_node(self, node_id: Union[str, KademliaNode], address: Optional[str] = None) -> bool:
        if isinstance(node_id, KademliaNode):
            nid = node_id.node_id
            addr = node_id.address
        else:
            nid = node_id
            addr = address or "127.0.0.1"
        if nid == self.local_node_id:
            return False
        index = self._bucket_index(nid)
        with self._lock:
            return self.buckets[index].update(nid, addr)

    def remove_node(self, node_id: str) -> None:
        index = self._bucket_index(node_id)
        with self._lock:
            self.buckets[index].remove(node_id)

    def find_close_nodes(self, target_id: str, count: int = 20) -> List[Any]:
        all_contacts: List[Tuple[str, str]] = []
        with self._lock:
            for bucket in self.buckets:
                all_contacts.extend(bucket.get_contacts())
        seen = set()
        unique_contacts = []
        for nid, addr in all_contacts:
            if nid not in seen and nid != self.local_node_id:
                seen.add(nid)
                unique_contacts.append((nid, addr))
        unique_contacts.sort(key=lambda item: xor_distance(item[0], target_id))
        return [KademliaNode(nid, addr, 9000) for nid, addr in unique_contacts[:count]]

    def store(self, key: str, value: Any) -> None:
        self.storage[key] = value

    def get(self, key: str) -> Any:
        return self.storage.get(key)
