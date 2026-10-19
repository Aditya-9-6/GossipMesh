from typing import Any, List, Optional, Tuple
import threading


class SkipListNode:
    def __init__(self, key: str, value: Any, level: int):
        self.key = key
        self.value = value
        self.forward: List[Optional["SkipListNode"]] = [None] * level


class SkipListRoutingTable:
    """Probabilistic SkipList routing table for O(log N) peer lookups."""

    def __init__(self, max_level: int = 16, p: float = 0.5):
        self.max_level = max_level
        self.p = p
        self.header = SkipListNode("", None, max_level)
        self.level = 1

    def insert(self, key: str, value: Any) -> None:
        update: List[Optional[SkipListNode]] = [None] * self.max_level
        current = self.header
        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < key:
                current = current.forward[i]
            update[i] = current

        current = current.forward[0]
        if current and current.key == key:
            current.value = value
            return

        import random

        lvl = 1
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1

        if lvl > self.level:
            for i in range(self.level, lvl):
                update[i] = self.header
            self.level = lvl

        node = SkipListNode(key, value, lvl)
        for i in range(lvl):
            up_node = update[i]
            if up_node is not None:
                node.forward[i] = up_node.forward[i]
                up_node.forward[i] = node

    def search(self, key: str) -> Optional[Any]:
        current = self.header
        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < key:
                current = current.forward[i]
        current = current.forward[0]
        if current and current.key == key:
            return current.value
        return None

    def delete(self, key: str) -> None:
        update: List[Optional[SkipListNode]] = [None] * self.max_level
        current = self.header
        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < key:
                current = current.forward[i]
            update[i] = current

        current = current.forward[0]
        if current and current.key == key:
            for i in range(self.level):
                up_node = update[i]
                if up_node is not None and up_node.forward[i] == current:
                    up_node.forward[i] = current.forward[i]
            while self.level > 1 and self.header.forward[self.level - 1] is None:
                self.level -= 1

    def get_all(self) -> List[Any]:
        res: List[Any] = []
        current = self.header.forward[0]
        while current:
            res.append(current.value)
            current = current.forward[0]
        return res


class ConcurrentSkipListRoutingTable:
    """Thread-safe capacity-bounded wrapper around SkipListRoutingTable."""

    def __init__(self, max_level: int = 16, p: float = 0.5, capacity: int = 10000) -> None:
        self.capacity = capacity
        self._table = SkipListRoutingTable(max_level=max_level, p=p)
        self._keys: list[str] = []
        self._lock = threading.Lock()
        self.size = 0

    def insert(self, key: str, *args: Any) -> None:
        value = args[0] if len(args) == 1 else args
        with self._lock:
            existing = self._table.search(key)
            if existing is None and self.size >= self.capacity:
                if self._keys:
                    old_key = self._keys.pop(0)
                    self._table.delete(old_key)
                    self.size = max(0, self.size - 1)
            if existing is None:
                self._keys.append(key)
                self.size += 1
            self._table.insert(key, value)

    def search(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._table.search(key)

    def delete(self, key: str) -> bool:
        with self._lock:
            val = self._table.search(key)
            if val is not None:
                self._table.delete(key)
                if key in self._keys:
                    self._keys.remove(key)
                self.size = max(0, self.size - 1)
                return True
            return False

    def get_all(self) -> List[Any]:
        with self._lock:
            return self._table.get_all()
