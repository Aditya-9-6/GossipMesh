import random
import threading
from typing import Any, Dict, List, Optional, Tuple


class SkipListNode:
    __slots__ = ("key", "score", "latency", "forward", "lock")

    def __init__(self, key: str, score: float, latency: float, level: int):
        self.key = key
        self.score = score
        self.latency = latency
        self.forward: List[Optional["SkipListNode"]] = [None] * level
        self.lock = threading.Lock()


class ConcurrentSkipListRoutingTable:
    def __init__(self, max_level: int = 16, p: float = 0.5, capacity: int = 1000):
        self.max_level = max_level
        self.p = p
        self.capacity = capacity
        self.head = SkipListNode("", float("inf"), 0.0, max_level)
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
            update = [None] * self.max_level
            curr = self.head
            for i in range(self.level - 1, -1, -1):
                while curr.forward[i] and curr.forward[i].key < key:
                    curr = curr.forward[i]
                update[i] = curr
            curr = curr.forward[0]
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
                node.forward[i] = update[i].forward[i]
                update[i].forward[i] = node
            self.size += 1
            if self.size > self.capacity:
                self._evict_worst()

    def _evict_worst(self) -> None:
        curr = self.head
        worst_node = None
        worst_score = float("-inf")
        while curr.forward[0]:
            nxt = curr.forward[0]
            if nxt.score > worst_score:
                worst_score = nxt.score
                worst_node = nxt
            curr = nxt

        if not worst_node:
            return

        update = [None] * self.max_level
        curr = self.head
        for i in range(self.level - 1, -1, -1):
            while curr.forward[i] and curr.forward[i] != worst_node:
                curr = curr.forward[i]
            update[i] = curr

        for i in range(len(worst_node.forward)):
            if i < len(update) and update[i] and update[i].forward[i] == worst_node:
                update[i].forward[i] = worst_node.forward[i]

        while self.level > 1 and self.head.forward[self.level - 1] is None:
            self.level -= 1

        self.size -= 1

    def search(self, key: str) -> Optional[Tuple[float, float]]:
        curr = self.head
        for i in range(self.level - 1, -1, -1):
            while curr.forward[i] and curr.forward[i].key < key:
                curr = curr.forward[i]
        curr = curr.forward[0]
        if curr and curr.key == key:
            return (curr.score, curr.latency)
        return None

    def delete(self, key: str) -> bool:
        with self._global_lock:
            update = [None] * self.max_level
            curr = self.head
            for i in range(self.level - 1, -1, -1):
                while curr.forward[i] and curr.forward[i].key < key:
                    curr = curr.forward[i]
                update[i] = curr
            curr = curr.forward[0]
            if not curr or curr.key != key:
                return False
            for i in range(self.level):
                if update[i].forward[i] != curr:
                    break
                update[i].forward[i] = curr.forward[i]
            while self.level > 1 and self.head.forward[self.level - 1] is None:
                self.level -= 1
            self.size -= 1
            return True

    def get_top_peers(self, limit: int = 10) -> List[Dict[str, Any]]:
        res = []
        curr = self.head.forward[0]
        while curr and len(res) < limit:
            res.append({"key": curr.key, "score": curr.score, "latency": curr.latency})
            curr = curr.forward[0]
        return res
