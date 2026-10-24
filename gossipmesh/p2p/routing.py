from __future__ import annotations

import random
import threading
from typing import Any, List, Optional, Tuple, Dict


class SkipListNode:
    def __init__(self, key: str, value: Any, level: int, score: float = 0.0, latency: float = 0.0):
        self.key = key
        self.value = value
        self.score = score
        self.latency = latency
        self.forward: List[Optional["SkipListNode"]] = [None] * level


class SkipList:
    def __init__(self, capacity: int = 10000, max_level: int = 16, p: float = 0.5):
        self.capacity = capacity
        self.max_level = max_level
        self.p = p
        self.size = 0
        self.header = SkipListNode("", None, max_level, float("-inf"), 0.0)
        self.level = 1
        self._global_lock = threading.RLock()

    def _random_level(self) -> int:
        lvl = 1
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl

    def search(self, key: str) -> Any:
        with self._global_lock:
            current = self.header
            for i in range(self.level - 1, -1, -1):
                while current.forward[i] and current.forward[i].key < key:
                    current = current.forward[i]
            current = current.forward[0]
            if current and current.key == key:
                if current.score != 0.0 or current.latency != 0.0:
                    return (current.score, current.latency)
                return current.value
            return None

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
                up = update[i]
                if up:
                    node.forward[i] = up.forward[i]
                    up.forward[i] = node
            self.size += 1
            if self.size > self.capacity:
                self._evict_worst()

    def delete(self, key: str) -> bool:
        with self._global_lock:
            update: List[Optional[SkipListNode]] = [None] * self.max_level
            current = self.header
            for i in range(self.level - 1, -1, -1):
                while current.forward[i] and current.forward[i].key < key:
                    current = current.forward[i]
                update[i] = current

            current = current.forward[0]
            if not current or current.key != key:
                return False

            for i in range(self.level):
                up = update[i]
                if not up or up.forward[i] != current:
                    break
                up.forward[i] = current.forward[i]

            while self.level > 1 and self.header.forward[self.level - 1] is None:
                self.level -= 1
            self.size -= 1
            return True

    def range_query(self, start_key: str, end_key: str) -> List[Tuple[str, Any]]:
        with self._global_lock:
            res: List[Tuple[str, Any]] = []
            current = self.header.forward[0]
            while current:
                if start_key <= current.key <= end_key:
                    res.append((current.key, current.value))
                elif current.key > end_key:
                    break
                current = current.forward[0]
            return res

    def get_top_peers(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._global_lock:
            res: List[Dict[str, Any]] = []
            curr = self.header.forward[0]
            while curr and len(res) < limit:
                res.append({"key": curr.key, "score": curr.score, "latency": curr.latency, "value": curr.value})
                curr = curr.forward[0]
            return res

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

        for i in range(self.level):
            up = update[i] if i < len(update) else None
            if up and up.forward[i] == worst_node:
                up.forward[i] = worst_node.forward[i]

        while self.level > 1 and self.header.forward[self.level - 1] is None:
            self.level -= 1

        self.size -= 1


class P2PRoutingTable(SkipList):
    """Probabilistic Skip List based routing table for peer discovery and key-value indexing."""

    def __init__(self, max_levels: int = 16, p: float = 0.5):
        super().__init__(max_level=max_levels, p=p)


class SkipListRoutingTable(SkipList):
    """Alias or subclass of SkipList for backward compatibility with routing table naming."""

    pass


class ConcurrentSkipListRoutingTable:
    """Thread-safe routing table wrapping SkipList with capacity and extra compatibility methods."""

    def __init__(self, max_level: int = 16, p: float = 0.5, capacity: int = 1000):
        self.capacity = capacity
        self.table = SkipList(max_level=max_level, p=p, capacity=capacity)
        self._size = 0
        self._lock = threading.Lock()

    @property
    def size(self) -> int:
        with self._lock:
            return self._size

    def insert(self, key: str, *args: Any) -> None:
        if len(args) == 1:
            val = args[0]
        elif len(args) > 1:
            val = args
        else:
            val = None

        with self._lock:
            existing = self.table.search(key)
            if existing is None:
                self._size += 1
            self.table.insert(key, val)

    def search(self, key: str) -> Any:
        with self._lock:
            return self.table.search(key)

    def delete(self, key: str) -> bool:
        with self._lock:
            existing = self.table.search(key)
            if existing is not None:
                self.table.delete(key)
                self._size = max(0, self._size - 1)
                return True
            return False

    def range_query(self, start_key: str, end_key: str) -> List[Tuple[str, Any]]:
        with self._lock:
            return self.table.range_query(start_key, end_key)
