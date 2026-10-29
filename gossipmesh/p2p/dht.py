import hashlib
import threading
import time
from typing import Dict, List, Optional, Tuple


def id_to_bytes(node_id: str) -> bytes:
    if len(node_id) == 64 and all(c in "0123456789abcdefABCDEF" for c in node_id):
        return bytes.fromhex(node_id)
    return hashlib.sha256(node_id.encode("utf-8")).digest()


def xor_distance(id1: str, id2: str) -> int:
    b1 = id_to_bytes(id1)
    b2 = id_to_bytes(id2)
    val1 = int.from_bytes(b1, byteorder="big")
    val2 = int.from_bytes(b2, byteorder="big")
    return val1 ^ val2


class KademliaNodeInfo:
    def __init__(self, node_id: str, address: str) -> None:
        self.node_id = node_id
        self.address = address
        self.last_seen = time.time()

    def update_seen(self) -> None:
        self.last_seen = time.time()


class KBucket:
    def __init__(self, k: int = 20) -> None:
        self.k = k
        self.nodes: List[KademliaNodeInfo] = []
        self._lock = threading.Lock()

    def add_node(self, node: KademliaNodeInfo) -> bool:
        with self._lock:
            for existing in self.nodes:
                if existing.node_id == node.node_id:
                    existing.address = node.address
                    existing.update_seen()
                    self.nodes.remove(existing)
                    self.nodes.append(existing)
                    return True
            if len(self.nodes) < self.k:
                self.nodes.append(node)
                return True
            return False

    def remove_node(self, node_id: str) -> None:
        with self._lock:
            self.nodes = [n for n in self.nodes if n.node_id != node_id]

    def get_nodes(self) -> List[KademliaNodeInfo]:
        with self._lock:
            return list(self.nodes)


class KademliaDHT:
    def __init__(self, local_node_id: str, k: int = 20, alpha: int = 3) -> None:
        self.local_node_id = local_node_id
        self.k = k
        self.alpha = alpha
        self.buckets: List[KBucket] = [KBucket(k) for _ in range(256)]
        self._lock = threading.Lock()

    def _get_bucket_index(self, node_id: str) -> int:
        dist = xor_distance(self.local_node_id, node_id)
        if dist == 0:
            return 0
        return dist.bit_length() - 1

    def add_node(self, node_id: str, address: str) -> bool:
        if node_id == self.local_node_id:
            return False
        node = KademliaNodeInfo(node_id, address)
        idx = self._get_bucket_index(node_id)
        if idx < 0 or idx >= len(self.buckets):
            idx = len(self.buckets) - 1
        return self.buckets[idx].add_node(node)

    def remove_node(self, node_id: str) -> None:
        idx = self._get_bucket_index(node_id)
        if 0 <= idx < len(self.buckets):
            self.buckets[idx].remove_node(node_id)

    def find_close_nodes(self, target_id: str, count: Optional[int] = None) -> List[KademliaNodeInfo]:
        if count is None:
            count = self.k
        all_nodes: List[Tuple[int, KademliaNodeInfo]] = []
        with self._lock:
            for bucket in self.buckets:
                for node in bucket.get_nodes():
                    dist = xor_distance(target_id, node.node_id)
                    all_nodes.append((dist, node))
        all_nodes.sort(key=lambda x: x[0])
        return [node for _, node in all_nodes[:count]]
