from typing import List, Optional
import threading
import random


class SkipListNode:
    def __init__(self, key: str, score: float, latency: float, level: int):
        self.key = key
        self.score = score
        self.latency = latency
        self.forward: List[Optional["SkipListNode"]] = [None] * level


class ConcurrentSkipListRoutingTable:
    def __init__(self, capacity: int = 10000, max_level: int = 16, p: float = 0.5):
        self.capacity = capacity
        self.max_level = max_level
        self.p = p
        self.head = SkipListNode("", float("-inf"), 0.0, max_level)
        self.level = 1
        self.size = 0
        self._global_lock = threading.Lock()

    def _random_level(self) -> int:
        lvl = 1
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl

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

            lvl = self._random_level()
            if lvl > self.level:
                for i in range(self.level, lvl):
                    update[i] = self.head
                self.level = lvl
            node = SkipListNode(key, score, latency, lvl)
            for i in range(lvl):
                up = update[i]
                node.forward[i] = up.forward[i] if up else None
                if up:
                    up.forward[i] = node
            self.size += 1
            if self.size > self.capacity:
                self._evict_worst()

    def _evict_worst(self) -> None:
        curr: Optional[SkipListNode] = self.head
        worst_node = None
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

        for i in range(self.level):
            up = update[i]
            if up and up.forward[i] == worst_node:
                up.forward[i] = worst_node.forward[i]
        self.size -= 1
