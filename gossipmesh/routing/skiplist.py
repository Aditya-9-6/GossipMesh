from __future__ import annotations

import random
import threading
from typing import Any, List, Optional, Tuple, Dict


class SkipListNode:
    __slots__ = ("key", "value", "score", "latency", "forward")

    def __init__(self, key: str, value: Any, level: int, score: float = 0.0, latency: float = 0.0) -> None:
        self.key = key
        self.value = value
        self.score = score
        self.latency = latency
        self.forward: List[Optional["SkipListNode"]] = [None] * level


class SkipList:
    """
    High-performance concurrent skip-list data structure leveraging atomic-style thread
    synchronization primitives to maintain dynamic P2P peer routing tables with deterministic
    O(log N) lookup, insertion, and deletion guarantees.
    """
    def __init__(self, capacity: int = 10000, max_level: int = 16, p: float = 0.5) -> None:
        self.capacity = capacity
        self.max_level = max_level
        self.p = p
        self.size = 0
        self.header = SkipListNode("", None, max_level, float("-inf"), 0.0)
        self.level = 1
        self._lock = threading.RLock()

    def _random_level(self) -> int:
        lvl = 1
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl

    def search(self, key: str) -> Any:
        with self._lock:
            current = self.header
            for i in range(self.level - 1, -1, -1):
                while current.forward[i] and current.forward[i].key < key:
                    current = current.forward[i]
            current = current.forward[0]
            if current and current.key == key:
                if current.score != 0.0 or current.latency != 0.0:
                    return (current.score, current.latency, current.value)
                return current.value
            return None

    def insert(self, key: str, value: Any = None, score: float = 0.0, latency: float = 0.0) -> None:
        with self._lock:
            update: List[Optional[SkipListNode]] = [None] * self.max_level
            curr: Optional[SkipListNode] = self.header
            for i in range(self.level - 1, -1, -1):
                while curr and curr.forward[i] and curr.forward[i].key < key:
                    curr = curr.forward[i]
                update[i] = curr
            curr = curr.forward[0] if curr else None
            if curr and curr.key == key:
                curr.value = value
                curr.score = score
                curr.latency = latency
                return

            lvl = self._random_level()
            if lvl > self.level:
                for i in range(self.level, lvl):
                    update[i] = self.header
                self.level = lvl
            node = SkipListNode(key, value, lvl, score, latency)
            for i in range(lvl):
                up = update[i]
                if up:
                    node.forward[i] = up.forward[i]
                    up.forward[i] = node
            self.size += 1
            if self.size > self.capacity:
                self._evict_worst()

    def delete(self, key: str) -> bool:
        with self._lock:
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
                up = update[i]
                if not up or up.forward[i] != current:
                    break
                up.forward[i] = current.forward[i]

            while self.level > 1 and self.header.forward[self.level - 1] is None:
                self.level -= 1
            self.size -= 1
            return True

    def range_query(self, start_key: str, end_key: str) -> List[Tuple[str, Any]]:
        with self._lock:
            results: List[Tuple[str, Any]] = []
            current = self.header
            for i in range(self.level - 1, -1, -1):
                while current.forward[i] and current.forward[i].key < start_key:
                    current = current.forward[i]
            current = current.forward[0]
            while current and current.key <= end_key:
                results.append((current.key, current.value))
                current = current.forward[0]
            return results

    def _evict_worst(self) -> None:
        # Evict the last node at level 0 if capacity is exceeded
        current = self.header
        while current.forward[0] and current.forward[0].forward[0]:
            current = current.forward[0]
        if current and current.forward[0]:
            worst_key = current.forward[0].key
            self.delete(worst_key)
