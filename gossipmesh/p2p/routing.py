from typing import List, Optional, Any, Tuple
import threading
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

    def delete(self, key: str) -> bool:
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
            return True
        return False

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
