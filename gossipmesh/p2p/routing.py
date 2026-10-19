from typing import Optional, List, Any
import random


class SkipListNode:
    def __init__(self, key: str, value: Any, level: int):
        self.key = key
        self.value = value
        self.forward: List[Optional["SkipListNode"]] = [None] * level


class SkipListRoutingTable:
    """Routing table implemented using a Skip List for decentralized node discovery."""

    def __init__(self, max_level: int = 16, p: float = 0.25):
        self.max_level = max_level
        self.p = p
        self.head = SkipListNode("", None, max_level)
        self.level = 1

    def _random_level(self) -> int:
        lvl = 1
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl

    def insert(self, key: str, value: Any) -> None:
        update: List[Optional[SkipListNode]] = [None] * self.max_level
        current = self.head

        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < key:
                current = current.forward[i]  # type: ignore
            update[i] = current

        current = current.forward[0]

        if current and current.key == key:
            current.value = value
            return

        lvl = self._random_level()
        if lvl > self.level:
            for i in range(self.level, lvl):
                update[i] = self.head
            self.level = lvl

        new_node = SkipListNode(key, value, lvl)
        for i in range(lvl):
            up_node = update[i]
            if up_node is not None:
                new_node.forward[i] = up_node.forward[i]
                up_node.forward[i] = new_node

    def search(self, key: str) -> Optional[Any]:
        current = self.head
        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < key:
                current = current.forward[i]  # type: ignore

        current = current.forward[0]
        if current and current.key == key:
            return current.value
        return None

    def delete(self, key: str) -> bool:
        update: List[Optional[SkipListNode]] = [None] * self.max_level
        current = self.head

        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < key:
                current = current.forward[i]  # type: ignore
            update[i] = current

        current = current.forward[0]

        if not current or current.key != key:
            return False

        for i in range(self.level):
            up_node = update[i]
            if up_node is None or up_node.forward[i] != current:
                break
            up_node.forward[i] = current.forward[i]

        while self.level > 1 and self.head.forward[self.level - 1] is None:
            self.level -= 1
        return True

    def range_query(self, start_key: str, end_key: str) -> List[Tuple[str, Any]]:
        res: List[Tuple[str, Any]] = []
        current = self.head
        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < start_key:
                current = current.forward[i]  # type: ignore

        current = current.forward[0]
        while current and (not end_key or current.key <= end_key):
            res.append((current.key, current.value))
            current = current.forward[0]
        return res
