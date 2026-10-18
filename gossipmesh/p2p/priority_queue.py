import time
import heapq
import threading
from typing import Any, Optional, Tuple

class PriorityQueueMessage:
    def __init__(self, priority: int, payload: Any, age_increment: int = 1):
        self.priority = priority
        self.payload = payload
        self.age_increment = age_increment
        self.timestamp = time.time()
        self.generation = 0

    def __lt__(self, other: 'PriorityQueueMessage') -> bool:
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


class WeightedPriorityQueue:
    def __init__(self, aging_factor: float = 0.05, max_size: int = 10000):
        self._queue: list = []
        self._lock = threading.Lock()
        self._aging_factor = aging_factor
        self._max_size = max_size

    def push(self, priority: int, payload: Any) -> bool:
        with self._lock:
            if len(self._queue) >= self._max_size:
                return False
            msg = PriorityQueueMessage(priority=priority, payload=payload)
            heapq.heappush(self._queue, msg)
            return True

    def pop(self) -> Optional[Any]:
        with self._lock:
            if not self._queue:
                return None
            self._age_queue_unlocked()
            msg = heapq.heappop(self._queue)
            return msg.payload

    def _age_queue_unlocked(self):
        current_time = time.time()
        if not self._queue:
            return
        for msg in self._queue:
            elapsed = current_time - msg.timestamp
            if elapsed > 0:
                boost = int(elapsed * self._aging_factor)
                if boost > 0:
                    msg.priority = max(0, msg.priority - boost)
                    msg.timestamp = current_time
        heapq.heapify(self._queue)

    def qsize(self) -> int:
        with self._lock:
            return len(self._queue)
