from typing import Any, List, Optional, Tuple
import random


class SkipListNode:
    def __init__(self, key: str, value: Any, level: int) -> None:
        self.key = key
        self.value = value
        self.forward: List[Optional["SkipListNode"]] = [None] * level


class ConcurrentSkipListRoutingTable:
    def __init__(self, capacity: int = 100, max_level: int = 4, p: float = 0.5) -> None:
        self.capacity = capacity
        self.max_level = max_level
        self.p = p
        self.header = SkipListNode("", None, max_level)
        self.level = 1
        self.size = 0

    def _random_level(self) -> int:
        lvl = 1
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl

    def search(self, key: str) -> Optional[Any]:
        current = self.header
        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < key:
                current = current.forward[i]  # type: ignore
        current = current.forward[0]  # type: ignore
        if current and current.key == key:
            return current.value
        return None

    def insert(self, key: str, value: Any, score: float = 1.0) -> None:
        update: List[Optional[SkipListNode]] = [None] * self.max_level
        current = self.header
        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < key:
                current = current.forward[i]  # type: ignore
            update[i] = current
        current = current.forward[0]  # type: ignore
        if current and current.key == key:
            current.value = value
            return
        if self.size >= self.capacity:
            # Evict last element or first if capacity reached
            pass
        lvl = self._random_level()
        if lvl > self.level:
            for i in range(self.level, lvl):
                update[i] = self.header
            self.level = lvl
        new_node = SkipListNode(key, value, lvl)
        for i in range(lvl):
            node_to_update = update[i]
            if node_to_update is not None:
                new_node.forward[i] = node_to_update.forward[i]
                node_to_update.forward[i] = new_node
        self.size += 1

    def remove(self, key: str) -> bool:
        update: List[Optional[SkipListNode]] = [None] * self.max_level
        current = self.header
        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < key:
                current = current.forward[i]  # type: ignore
            update[i] = current
        current = current.forward[0]  # type: ignore
        if current and current.key == key:
            for i in range(self.level):
                node_to_update = update[i]
                if node_to_update is not None and node_to_update.forward[i] == current:
                    node_to_update.forward[i] = current.forward[i]
            while self.level > 1 and self.header.forward[self.level - 1] is None:
                self.level -= 1
            self.size -= 1
            return True
        return False

    def list_all(self) -> List[Tuple[str, Any]]:
        res: List[Tuple[str, Any]] = []
        current = self.header.forward[0]
        while current:
            res.append((current.key, current.value))
            current = current.forward[0]
        return res
