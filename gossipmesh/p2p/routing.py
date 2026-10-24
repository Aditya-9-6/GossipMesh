from typing import List, Optional, Any


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

    def search(self, key: str) -> Any:
        current = self.header
        for i in range(self.level - 1, -1, -1):
            while current.forward[i] and current.forward[i].key < key:
                current = current.forward[i]
        current = current.forward[0]
        if current and current.key == key:
            return current.value
        return None

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

        level = 1
        while random.random() < self.p and level < self.max_level:
            level += 1

        if level > self.level:
            for i in range(self.level, level):
                update[i] = self.header
            self.level = level

        new_node = SkipListNode(key, value, level)
        for i in range(level):
            new_node.forward[i] = update[i].forward[i] if update[i] else None
            if update[i]:
                update[i].forward[i] = new_node

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
                if update[i] and update[i].forward[i] != current:
                    break
                if update[i]:
                    update[i].forward[i] = current.forward[i]

            while self.level > 1 and self.header.forward[self.level - 1] is None:
                self.level -= 1

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
