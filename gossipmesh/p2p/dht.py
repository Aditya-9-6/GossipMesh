import hashlib
import time
import asyncio
from typing import List, Dict, Tuple, Optional, Any

K = 20  # Bucket size
ALPHA = 3  # Concurrency parameter for lookups
ID_BITS = 160  # SHA-1 bit length

class DHTNode:
    def __init__(self, node_id: str, host: str, port: int):
        self.node_id = node_id
        self.numeric_id = int(hashlib.sha1(node_id.encode('utf-8')).hexdigest(), 16)
        self.host = host
        self.port = port
        self.last_seen = time.time()

    def update_seen(self):
        self.last_seen = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "host": self.host,
            "port": self.port,
            "last_seen": self.last_seen
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DHTNode':
        node = cls(data["node_id"], data["host"], data["port"])
        node.last_seen = data.get("last_seen", time.time())
        return node


class KBucket:
    def __init__(self, range_min: int, range_max: int, k: int = K):
        self.range_min = range_min
        self.range_max = range_max
        self.k = k
        self.nodes: List[DHTNode] = []
        self.lock = asyncio.Lock()

    async def add_node(self, node: DHTNode) -> bool:
        async with self.lock:
            for i, existing in enumerate(self.nodes):
                if existing.node_id == node.node_id:
                    existing.update_seen()
                    # Move to tail (most recently seen)
                    self.nodes.pop(i)
                    self.nodes.append(existing)
                    return True
            
            if len(self.nodes) < self.k:
                self.nodes.append(node)
                return True
            else:
                # Bucket is full. In a strict Kademlia, ping head node.
                # Here we drop if head is responsive or just keep tail-heavy LRU.
                return False

    async def remove_node(self, node_id: str):
        async with self.lock:
            self.nodes = [n for n in self.nodes if n.node_id != node_id]

    async def get_nodes(self) -> List[DHTNode]:
        async with self.lock:
            return list(self.nodes)


class KademliaDHT:
    def __init__(self, local_node: DHTNode):
        self.local_node = local_node
        self.buckets: List[KBucket] = []
        self._init_buckets()

    def _init_buckets(self):
        # Initialize a single bucket covering the entire 160-bit space
        self.buckets = [KBucket(0, 2**ID_BITS)]

    def _xor_distance(self, id1: int, id2: int) -> int:
        return id1 ^ id2

    def _find_bucket_index(self, numeric_id: int) -> int:
        for i, bucket in enumerate(self.buckets):
            if bucket.range_min <= numeric_id < bucket.range_max:
                return i
        return len(self.buckets) - 1

    async def add_node(self, node: DHTNode):
        if node.node_id == self.local_node.node_id:
            return
        idx = self._find_bucket_index(node.numeric_id)
        bucket = self.buckets[idx]
        success = await bucket.add_node(node)
        
        # If bucket is full and falls within local node range, split bucket
        if not success and bucket.range_min <= self.local_node.numeric_id < bucket.range_max:
            self._split_bucket(idx)
            # Retry adding
            idx = self._find_bucket_index(node.numeric_id)
            await self.buckets[idx].add_node(node)

    def _split_bucket(self, index: int):
        bucket = self.buckets[index]
        mid = (bucket.range_min + bucket.range_max) // 2
        left = KBucket(bucket.range_min, mid)
        right = KBucket(mid, bucket.range_max)
        
        # Redistribute nodes
        for node in bucket.nodes:
            if node.numeric_id < mid:
                left.nodes.append(node)
            else:
                right.nodes.append(node)

        self.buckets[index] = left
        self.buckets.insert(index + 1, right)

    async def find_close_nodes(self, target_id: str, count: int = K) -> List[DHTNode]:
        target_numeric = int(hashlib.sha1(target_id.encode('utf-8')).hexdigest(), 16)
        all_nodes = []
        for bucket in self.buckets:
            nodes = await bucket.get_nodes()
            all_nodes.extend(nodes)

        # Sort by XOR metric distance
        all_nodes.sort(key=lambda n: self._xor_distance(n.numeric_id, target_numeric))
        return all_nodes[:count]

    async def get_routing_table_stats(self) -> Dict[str, Any]:
        total_nodes = 0
        bucket_stats = []
        for i, b in enumerate(self.buckets):
            nodes = await b.get_nodes()
            count = len(nodes)
            total_nodes += count
            bucket_stats.append({"bucket": i, "range": (b.range_min, b.range_max), "size": count})
        return {
            "local_node": self.local_node.node_id,
            "total_peers": total_nodes,
            "buckets": bucket_stats
        }
