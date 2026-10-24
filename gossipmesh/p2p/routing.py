import random
import threading
from typing import Any, Dict, List, Optional


class SkipListNode:
    def __init__(self, key: str, value: Any, levels: int):
        self.key = key
        self.value = value
        self.forward: List[Optional["SkipListNode"]] = [None] * levels


class P2PRoutingTable:
    """Probabilistic Skip List based routing table for peer discovery and key-value indexing."""

    def __init__(self, max_levels: int = 16, p: float = 0.5):
        self.max_levels = max_levels
        self.p = p
        self.head = SkipListNode("", None, max_levels)
        self.level = 1

    def _random_level(self) -> int:
        lvl = 1
        while random.random() < self.p and lvl < self.max_levels:
            lvl += 1
        return lvl

    def insert(self, key: str, value: Any):
        update: List[Optional[SkipListNode]] = [None] * self.max_levels
        curr = self.head

        for i in range(self.level - 1, -1, -1):
            while curr.forward[i] is not None and curr.forward[i].key < key:
                curr = curr.forward[i]  # type: ignore
            update[i] = curr

        curr = curr.forward[0]  # type: ignore

        if curr is not None and curr.key == key:
            curr.value = value
            return

        lvl = self._random_level()
        if lvl > self.level:
            for i in range(self.level, lvl):
                update[i] = self.head
            self.level = lvl

        new_node = SkipListNode(key, value, lvl)
        for i in range(lvl):
            nxt = update[i].forward[i] if update[i] is not None else None
            new_node.forward[i] = nxt
            if update[i] is not None:
                update[i].forward[i] = new_node  # type: ignore

    def search(self, key: str) -> Optional[Any]:
        curr = self.head
        for i in range(self.level - 1, -1, -1):
            while curr.forward[i] is not None and curr.forward[i].key < key:
                curr = curr.forward[i]  # type: ignore

        curr = curr.forward[0]  # type: ignore
        if curr is not None and curr.key == key:
            return curr.value
        return None

    def delete(self, key: str) -> bool:
        update: List[Optional[SkipListNode]] = [None] * self.max_levels
        curr = self.head

        for i in range(self.level - 1, -1, -1):
            while curr.forward[i] is not None and curr.forward[i].key < key:
                curr = curr.forward[i]  # type: ignore
            update[i] = curr

        curr = curr.forward[0]  # type: ignore

        if curr is None or curr.key != key:
            return False

        for i in range(self.level):
            if update[i].forward[i] != curr:
                break
            update[i].forward[i] = curr.forward[i]  # type: ignore

        while self.level > 1 and self.head.forward[self.level - 1] is None:
            self.level -= 1

        return True

    def range_query(self, start_key: str, end_key: str) -> List[Dict[str, Any]]:
        res: List[Dict[str, Any]] = []
        curr = self.head
        for i in range(self.level - 1, -1, -1):
            while curr.forward[i] is not None and curr.forward[i].key < start_key:
                curr = curr.forward[i]  # type: ignore

        curr = curr.forward[0]  # type: ignore
        while curr is not None and curr.key <= end_key:
            res.append({"key": curr.key, "value": curr.value})
            curr = curr.forward[0]  # type: ignore

        return res


class ConcurrentSkipListRoutingTable(P2PRoutingTable):
    """Thread-safe extension of P2PRoutingTable with capacity constraints supporting test_routing.py."""

    def __init__(self, max_levels: int = 16, p: float = 0.5, capacity: Optional[int] = None):
        super().__init__(max_levels=max_levels, p=p)
        self.capacity = capacity
        self.size = 0
        self._lock = threading.Lock()

    def insert(self, key: str, *args: Any):
        with self._lock:
            val = args[0] if len(args) == 1 else args
            exists = self.search(key) is not None
            super().insert(key, val)
            if not exists:
                self.size += 1
                if self.capacity is not None and self.size > self.capacity:
                    # Evict last element if over capacity
                    curr = self.head.forward[0]
                    last_key = None
                    while curr is not None:
                        last_key = curr.key
                        curr = curr.forward[0]
                    if last_key is not None:
                        super().delete(last_key)
                        self.size -= 1

    def delete(self, key: str) -> bool:
        with self._lock:
            res = super().delete(key)
            if res:
                self.size = max(0, self.size - 1)
            return res

    def search(self, key: str) -> Optional[Any]:
        with self._lock:
            return super().search(key)
