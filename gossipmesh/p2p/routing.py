from typing import List, Optional, Any, Tuple, Dict
import threading
import random


class SkipListNode:
    def __init__(self, key: str, value: Any, level: int, score: float = 0.0, latency: float = 0.0):
        self.key = key
        self.value = value
        self.score = score
        self.latency = latency
        self.forward: List[Optional["SkipListNode"]] = [None] * level


class SkipList:
    def __init__(self, max_level: int = 16, p: float = 0.5, capacity: int = 1000):
        self.max_level = max_level
        self.p = p
        self.capacity = capacity
        self.size = 0
        self.header = SkipListNode("", None, max_level)
        self.level = 1
        self._global_lock = threading.RLock()

    def _random_level(self) -> int:
        lvl = 1
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl

    def insert(self, key: str, value: Any = None, score: float = 0.0, latency: float = 0.0) -> None:
        with self._global_lock:
            update: List[Optional[SkipListNode]] = [None] * self.max_level
            curr: Optional[SkipListNode] = self.header
            for i in range(self.level - 1, -1, -1):
                while curr and curr.forward[i] and curr.forward[i].key < key:
                    curr = curr.forward[i]
                update[i] = curr
            curr = curr.forward[0] if curr else None
            if curr and curr.key == key:
                curr.value = value
                curr.score = score
                curr.latency = latency
                return
            lvl = self._random_level()
            if lvl > self.level:
                for i in range(self.level, lvl):
                    update[i] = self.header
                self.level = lvl
            node = SkipListNode(key, value, lvl, score, latency)
            for i in range(lvl):
                up_node = update[i]
                if up_node:
                    node.forward[i] = up_node.forward[i]
                    up_node.forward[i] = node
            self.size += 1
            if self.size > self.capacity:
                self._evict_worst()

    def _evict_worst(self) -> None:
        curr: Optional[SkipListNode] = self.header
        worst_node = None
        worst_score = float("-inf")
        while curr and curr.forward[0]:
            nxt = curr.forward[0]
            if nxt and nxt.score > worst_score:
                worst_score = nxt.score
                worst_node = nxt
            curr = nxt

        if not worst_node:
            return

        update: List[Optional[SkipListNode]] = [None] * self.max_level
        curr = self.header
        for i in range(self.level - 1, -1, -1):
            while curr and curr.forward[i] and curr.forward[i] != worst_node:
                curr = curr.forward[i]
            update[i] = curr

        for i in range(len(worst_node.forward)):
            up_node = update[i] if i < len(update) else None
            if up_node and up_node.forward[i] == worst_node:
                up_node.forward[i] = worst_node.forward[i]

        while self.level > 1 and self.header.forward[self.level - 1] is None:
            self.level -= 1

        self.size -= 1

    def search(self, key: str) -> Any:
        curr: Optional[SkipListNode] = self.header
        for i in range(self.level - 1, -1, -1):
            while curr and curr.forward[i] and curr.forward[i].key < key:
                curr = curr.forward[i]
        curr = curr.forward[0] if curr else None
        if curr and curr.key == key:
            if curr.score != 0.0 or curr.latency != 0.0:
                return (curr.score, curr.latency)
            return curr.value
        return None

    def delete(self, key: str) -> bool:
        with self._global_lock:
            update: List[Optional[SkipListNode]] = [None] * self.max_level
            curr: Optional[SkipListNode] = self.header
            for i in range(self.level - 1, -1, -1):
                while curr and curr.forward[i] and curr.forward[i].key < key:
                    curr = curr.forward[i]
                update[i] = curr
            curr = curr.forward[0] if curr else None
            if not curr or curr.key != key:
                return False
            for i in range(self.level):
                up_node = update[i]
                if not up_node or up_node.forward[i] != curr:
                    break
                up_node.forward[i] = curr.forward[i]
            while self.level > 1 and self.header.forward[self.level - 1] is None:
                self.level -= 1
            self.size -= 1
            return True

    def get_top_peers(self, limit: int = 10) -> List[Dict[str, Any]]:
        res: List[Dict[str, Any]] = []
        curr = self.header.forward[0]
        while curr and len(res) < limit:
            res.append({"key": curr.key, "score": curr.score, "latency": curr.latency, "value": curr.value})
            curr = curr.forward[0]
        return res

    def range_query(self, start_key: str, end_key: str) -> List[Any]:
        res: List[Any] = []
        current = self.header
        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < start_key:
                current = current.forward[i]

        current = current.forward[0]
        while current and current.key <= end_key:
            res.append(current.value)
            current = current.forward[0]
        return res


class ConcurrentSkipListRoutingTable:
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.skip_list = SkipList()
        self._lock = threading.Lock()
        self._size = 0

    @property
    def size(self) -> int:
        with self._lock:
            return self._size

    def insert(self, key: str, *values: Any) -> None:
        val = values[0] if len(values) == 1 else values
        with self._lock:
            existing = self.skip_list.search(key)
            if existing is None:
                if self._size >= self.capacity:
                    # Evict some or skip
                    pass
                self._size += 1
            self.skip_list.insert(key, val)

    def search(self, key: str) -> Any:
        with self._lock:
            return self.skip_list.search(key)

    def delete(self, key: str) -> bool:
        with self._lock:
            res = self.skip_list.delete(key)
            if res:
                self._size = max(0, self._size - 1)
            return res

    def range_query(self, start_key: str, end_key: str) -> List[Any]:
        with self._lock:
            return self.skip_list.range_query(start_key, end_key)
