from typing import Any, Optional
from gossipmesh.p2p.priority_queue import WeightedPriorityQueue

class GossipRouter:
    def __init__(self, aging_factor: float = 0.05, max_size: int = 10000):
        self.pq = WeightedPriorityQueue(aging_factor=aging_factor, max_size=max_size)

    def enqueue_message(self, priority: int, payload: Any) -> bool:
        return self.pq.push(priority, payload)

    def dequeue_message(self) -> Optional[Any]:
        return self.pq.pop()

    def queue_size(self) -> int:
        return self.pq.qsize()
