from typing import Any, Dict, List, Optional, Tuple
import threading
import random


class SkipListNode:
    def __init__(self, key: str, value: Any = None, level: int = 16, score: float = 0.0, latency: float = 0.0):
        self.key = key
        self.value = value
        self.score = score
        self.latency = latency
        self.forward: List[Optional["SkipListNode"]] = [None] * level


class ConcurrentSkipListRoutingTable:
    def __init__(self, capacity: int = 1000, max_level: int = 16):
        self.capacity = capacity
        self.max_level = max_level
        self.level = 1
        self.size = 0
        self.head = SkipListNode("", None, max_level, 0.0, 0.0)
        self._global_lock = threading.Lock()

    def insert(self, key: str, score: float, latency: float) -> None:
        with self._global_lock:
            update: List[Optional[SkipListNode]] = [None] * self.max_level
            curr: Optional[SkipListNode] = self.head
            for i in range(self.level - 1, -1, -1):
                while curr and curr.forward[i] and curr.forward[i].key < key:
                    curr = curr.forward[i]
                update[i] = curr
            curr = curr.forward[0] if curr else None
            if curr and curr.key == key:
                curr.score = score
                curr.latency = latency
                return

            lvl = 1
            while random.random() < 0.5 and lvl < self.max_level:
                lvl += 1
            if lvl > self.level:
                for i in range(self.level, lvl):
                    update[i] = self.head
                self.level = lvl
            node = SkipListNode(key, None, lvl, score, latency)
            for i in range(lvl):
                up_node = update[i]
                if up_node is not None:
                    node.forward[i] = up_node.forward[i]
                    up_node.forward[i] = node
            self.size += 1
            if self.size > self.capacity:
                self._evict_worst()

    def _evict_worst(self) -> None:
        curr: Optional[SkipListNode] = self.head
        worst_node: Optional[SkipListNode] = None
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
        curr = self.head
        for i in range(self.level - 1, -1, -1):
            while curr and curr.forward[i] and curr.forward[i] != worst_node:
                curr = curr.forward[i]
            update[i] = curr

        for i in range(len(worst_node.forward)):
            if i < len(update) and update[i] and update[i].forward[i] == worst_node:
                up_node = update[i]
                if up_node is not None:
                    up_node.forward[i] = worst_node.forward[i]

        while self.level > 1 and self.head.forward[self.level - 1] is None:
            self.level -= 1

        self.size -= 1

    def search(self, key: str) -> Optional[Tuple[float, float]]:
        curr: Optional[SkipListNode] = self.head
        for i in range(self.level - 1, -1, -1):
            while curr and curr.forward[i] and curr.forward[i].key < key:
                curr = curr.forward[i]
        curr = curr.forward[0] if curr else None
        if curr and curr.key == key:
            return (curr.score, curr.latency)
        return None

    def delete(self, key: str) -> bool:
        with self._global_lock:
            update: List[Optional[SkipListNode]] = [None] * self.max_level
            curr: Optional[SkipListNode] = self.head
            for i in range(self.level - 1, -1, -1):
                while curr and curr.forward[i] and curr.forward[i].key < key:
                    curr = curr.forward[i]
                update[i] = curr
            curr = curr.forward[0] if curr else None
            if not curr or curr.key != key:
                return False
            for i in range(self.level):
                up_node = update[i]
                if not up_node or up_node.forward[i] != curr:
                    break
                up_node.forward[i] = curr.forward[i]
            while self.level > 1 and self.head.forward[self.level - 1] is None:
                self.level -= 1
            self.size -= 1
            return True

    def get_top_peers(self, limit: int = 10) -> List[Dict[str, Any]]:
        res: List[Dict[str, Any]] = []
        curr = self.head.forward[0]
        while curr and len(res) < limit:
            res.append({"key": curr.key, "score": curr.score, "latency": curr.latency})
            curr = curr.forward[0]
        return res


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
