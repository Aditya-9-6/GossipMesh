from __future__ import annotations

import random
from typing import Any, List, Optional, Tuple


class SkipListNode:
    def __init__(self, key: str, value: Any, level: int):
        self.key = key
        self.value = value
        self.level = level
        self.forward: List[Optional[SkipListNode]] = [None] * (level + 1)


class SkipListRoutingTable:
    def __init__(self, max_level: int = 16, p: float = 0.5):
        self.max_level = max_level
        self.p = p
        self.head = SkipListNode("", None, max_level)
        self.level = 0

    def _random_level(self) -> int:
        lvl = 0
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl

    def insert(self, key: str, value: Any) -> None:
        update: List[Optional[SkipListNode]] = [None] * (self.max_level + 1)
        current = self.head

        for i in range(self.level, -1, -1):
            while current.forward[i] and current.forward[i].key < key:
                current = current.forward[i]
            update[i] = current

        current = current.forward[0]

        if current and current.key == key:
            current.value = value
            return

        lvl = self._random_level()
        if lvl > self.level:
            for i in range(self.level + 1, lvl + 1):
                update[i] = self.head
            self.level = lvl

        new_node = SkipListNode(key, value, lvl)
        for i in range(lvl + 1):
            up_node = update[i]
            if up_node is not None:
                new_node.forward[i] = up_node.forward[i]
                up_node.forward[i] = new_node

    def search(self, key: str) -> Any:
        current = self.head
        for i in range(self.level, -1, -1):
            while current.forward[i] and current.forward[i].key < key:
                current = current.forward[i]
        current = current.forward[0]
        if current and current.key == key:
            return current.value
        return None

    def delete(self, key: str) -> None:
        update: List[Optional[SkipListNode]] = [None] * (self.max_level + 1)
        current = self.head

        for i in range(self.level, -1, -1):
            while current.forward[i] and current.forward[i].key < key:
                current = current.forward[i]
            update[i] = current

        current = current.forward[0]
        if current and current.key == key:
            for i in range(self.level + 1):
                up_node = update[i]
                if up_node is None or up_node.forward[i] != current:
                    break
                if up_node is not None:
                    up_node.forward[i] = current.forward[i]

            while self.level > 0 and self.head.forward[self.level] is None:
                self.level -= 1

    def range_query(self, start_key: str, end_key: str) -> List[Any]:
        res: List[Any] = []
        current = self.head.forward[0]
        while current:
            if start_key <= current.key <= end_key:
                res.append((current.key, current.value))
            elif current.key > end_key:
                break
            current = current.forward[0]
        return res


class ConcurrentSkipListRoutingTable:
    """Thread-safe routing table wrapping SkipListRoutingTable with capacity and extra compatibility methods."""

    def __init__(self, max_level: int = 16, p: float = 0.5, capacity: int = 1000):
        self.capacity = capacity
        self.table = SkipListRoutingTable(max_level=max_level, p=p)
        self._size = 0
        import threading

        self._lock = threading.Lock()

    @property
    def size(self) -> int:
        with self._lock:
            return self._size

    def insert(self, key: str, *args: Any) -> None:
        # supports insert("key", val1, val2) or insert("key", val)
        if len(args) == 1:
            val = args[0]
        elif len(args) > 1:
            val = args
        else:
            val = None

        with self._lock:
            existing = self.table.search(key)
            if existing is None:
                if self._size >= self.capacity:
                    # evict oldest or simple approximation
                    pass
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
