from typing import List, Optional, Any
import random


class SkipListNode:
    def __init__(self, key: str, value: Any, level: int):
        self.key = key
        self.value = value
        self.forward: List[Optional["SkipListNode"]] = [None] * level


class SkipList:
    def __init__(self, max_level: int = 16, p: float = 0.5):
        self.max_level = max_level
        self.p = p
        self.header = SkipListNode("", None, max_level)
        self.level = 1

    def search(self, search_key: str) -> Any:
        current = self.header
        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < search_key:  # type: ignore
                current = current.forward[i]  # type: ignore
        current = current.forward[0]  # type: ignore
        if current and current.key == search_key:
            return current.value
        return None

    def insert(self, key: str, value: Any) -> None:
        update: List[Optional[SkipListNode]] = [None] * self.max_level
        current = self.header
        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < key:  # type: ignore
                current = current.forward[i]  # type: ignore
            update[i] = current

        current = current.forward[0]  # type: ignore
        if current and current.key == key:
            current.value = value
            return

        lvl = 1
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1

        if lvl > self.level:
            for i in range(self.level, lvl):
                update[i] = self.header
            self.level = lvl

        new_node = SkipListNode(key, value, lvl)
        for i in range(lvl):
            node_update = update[i]
            if node_update is not None:
                new_node.forward[i] = node_update.forward[i]
                node_update.forward[i] = new_node

    def delete(self, key: str) -> None:
        update: List[Optional[SkipListNode]] = [None] * self.max_level
        current = self.header
        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < key:  # type: ignore
                current = current.forward[i]  # type: ignore
            update[i] = current

        current = current.forward[0]  # type: ignore
        if current and current.key == key:
            for i in range(self.level):
                node_update = update[i]
                if node_update is not None and node_update.forward[i] != current:
                    break
                if node_update is not None:
                    node_update.forward[i] = current.forward[i]
            while self.level > 1 and self.header.forward[self.level - 1] is None:
                self.level -= 1

    def items(self) -> List[tuple]:
        res: List[tuple] = []
        current = self.header.forward[0]
        while current:
            res.append((current.key, current.value))
            current = current.forward[0]
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


class ConcurrentSkipListRoutingTable(SkipList):
    def __init__(self, max_level: int = 16, p: float = 0.5, capacity: int = 1000):
        super().__init__(max_level=max_level, p=p)
        self.capacity = capacity
        self.size = 0

    def insert(self, key: str, score: float, latency: float) -> None:
        super().insert(key, (score, latency))
        self.size = len(self.items())
        if self.size > self.capacity:
            items = self.items()
            if items:
                worst = max(items, key=lambda x: x[1][0])
                super().delete(worst[0])
                self.size = len(self.items())

    def delete(self, key: str) -> bool:
        res = self.search(key)
        if res is not None:
            super().delete(key)
            self.size = len(self.items())
            return True
        return False
