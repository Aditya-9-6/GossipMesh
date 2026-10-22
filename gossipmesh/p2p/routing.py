import random
import threading
from typing import Optional, List, Tuple, Dict, Any


class SkipListNode:
    def __init__(self, peer_id: str, latency: float, reliability: float, level: int):
        self.peer_id = peer_id
        self.latency = latency
        self.reliability = reliability
        self.forward: List[Optional["SkipListNode"]] = [None] * level


class ConcurrentSkipListRoutingTable:
    def __init__(self, max_level: int = 16, p: float = 0.5, capacity: int = 1000):
        self.max_level = max_level
        self.p = p
        self.capacity = capacity
        self.head = SkipListNode("", 0.0, 0.0, max_level)
        self.level = 1
        self._size = 0
        self.lock = threading.RLock()

    @property
    def size(self) -> int:
        return self._size

    def _random_level(self) -> int:
        lvl = 1
        while random.random() < self.p and lvl < self.max_level:
            lvl += 1
        return lvl

    def insert(self, peer_id: str, latency: float, reliability: float) -> None:
        with self.lock:
            update: List[Optional[SkipListNode]] = [None] * self.max_level
            curr = self.head
            for i in range(self.level - 1, -1, -1):
                while curr.forward[i] and curr.forward[i].peer_id < peer_id:
                    curr = curr.forward[i]
                update[i] = curr

            curr = curr.forward[0]

            if curr and curr.peer_id == peer_id:
                curr.latency = latency
                curr.reliability = reliability
                return

            # If at capacity, remove the worst or oldest entry if needed, or evict
            if self._size >= self.capacity:
                # Remove tail / last element or trim
                self._evict_one()

            lvl = self._random_level()
            if lvl > self.level:
                for i in range(self.level, lvl):
                    update[i] = self.head
                self.level = lvl

            node = SkipListNode(peer_id, latency, reliability, lvl)
            for i in range(lvl):
                node.forward[i] = update[i].forward[i] if update[i] else None
                if update[i]:
                    update[i].forward[i] = node
            self._size += 1

    def _evict_one(self) -> None:
        # Evict the last node at level 0
        curr = self.head
        prev = None
        while curr.forward[0]:
            prev = curr
            curr = curr.forward[0]
        if curr and curr.peer_id:
            self.delete(curr.peer_id)

    def delete(self, peer_id: str) -> bool:
        with self.lock:
            update: List[Optional[SkipListNode]] = [None] * self.max_level
            curr = self.head
            for i in range(self.level - 1, -1, -1):
                while curr.forward[i] and curr.forward[i].peer_id < peer_id:
                    curr = curr.forward[i]
                update[i] = curr

            curr = curr.forward[0]
            if curr and curr.peer_id == peer_id:
                for i in range(self.level):
                    if update[i] and update[i].forward[i] != curr:
                        break
                    if update[i]:
                        update[i].forward[i] = curr.forward[i]
                while self.level > 1 and self.head.forward[self.level - 1] is None:
                    self.level -= 1
                self._size = max(0, self._size - 1)
                return True
            return False

    def search(self, peer_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            curr = self.head
            for i in range(self.level - 1, -1, -1):
                while curr.forward[i] and curr.forward[i].peer_id < peer_id:
                    curr = curr.forward[i]
            curr = curr.forward[0]
            if curr and curr.peer_id == peer_id:
                return {
                    "peer_id": curr.peer_id,
                    "latency": curr.latency,
                    "reliability": curr.reliability,
                }
            return None
