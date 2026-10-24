import json
import random
import threading
from typing import Any, Dict, List, Optional, Tuple


class SkipListNode:
    def __init__(self, key: str, value: Any, level: int):
        self.key = key
        self.value = value
        self.forward: List[Optional["SkipListNode"]] = [None] * level


class SkipList:
    def __init__(self, max_level: int = 16, p: float = 0.5, capacity: int = 1000):
        self.max_level = max_level
        self.p = p
        self.capacity = capacity
        self.size = 0
        self.header = SkipListNode("", None, max_level)
        self.level = 1
        self._global_lock = threading.Lock()

    def _random_level(self) -> int:
        lvl = 1
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl

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
        with self._global_lock:
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

            level = self._random_level()

            if level > self.level:
                for i in range(self.level, level):
                    update[i] = self.header
                self.level = level

            new_node = SkipListNode(key, value, level)
            for i in range(level):
                new_node.forward[i] = update[i].forward[i] if update[i] else None
                if update[i]:
                    update[i].forward[i] = new_node

            self.size += 1
            if self.size > self.capacity:
                self._evict_worst()

    def _evict_worst(self) -> None:
        curr: Optional[SkipListNode] = self.header
        worst_node = None
        while curr and curr.forward[0]:
            nxt = curr.forward[0]
            if nxt:
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
            up = update[i] if i < len(update) else None
            if up and up.forward[i] == worst_node:
                up.forward[i] = worst_node.forward[i]

        while self.level > 1 and self.header.forward[self.level - 1] is None:
            self.level -= 1

        self.size -= 1

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
                if update[i] and update[i].forward[i] != current:
                    break
                if update[i]:
                    update[i].forward[i] = current.forward[i]

            while self.level > 1 and self.header.forward[self.level - 1] is None:
                self.level -= 1

            self.size -= 1
            return True

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

    def get_top_peers(self, limit: int = 10) -> List[Dict[str, Any]]:
        res: List[Dict[str, Any]] = []
        curr = self.header.forward[0]
        while curr and len(res) < limit:
            res.append({"key": curr.key, "value": curr.value})
            curr = curr.forward[0]
        return res
