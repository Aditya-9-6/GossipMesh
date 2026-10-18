import unittest
import time
from gossipmesh.p2p.priority_queue import WeightedPriorityQueue, PriorityQueueMessage
from gossipmesh.p2p.router import GossipRouter

class TestPriorityQueue(unittest.TestCase):
    def test_priority_ordering(self):
        pq = WeightedPriorityQueue()
        pq.push(10, "data-payload-low")
        pq.push(1, "control-heartbeat")
        pq.push(5, "medium-payload")

        self.assertEqual(pq.pop(), "control-heartbeat")
        self.assertEqual(pq.pop(), "medium-payload")
        self.assertEqual(pq.pop(), "data-payload-low")
        self.assertIsNone(pq.pop())

    def test_max_size_bound(self):
        pq = WeightedPriorityQueue(max_size=2)
        self.assertTrue(pq.push(1, "a"))
        self.assertTrue(pq.push(1, "b"))
        self.assertFalse(pq.push(1, "c"))
        self.assertEqual(pq.qsize(), 2)

    def test_aging_prevents_starvation(self):
        pq = WeightedPriorityQueue(aging_factor=10.0)
        # Push low priority message with old timestamp
        msg = PriorityQueueMessage(priority=100, payload="starving")
        msg.timestamp = time.time() - 2.0
        with pq._lock:
            pq._queue.append(msg)
            pq._queue.append(PriorityQueueMessage(priority=50, payload="normal"))
            import heapq
            heapq.heapify(pq._queue)

        popped = pq.pop()
        # Aging should have boosted 'starving' priority below 50
        self.assertEqual(popped, "starving")

    def test_router_integration(self):
        router = GossipRouter()
        router.enqueue_message(10, "low")
        router.enqueue_message(2, "high")
        self.assertEqual(router.queue_size(), 2)
        self.assertEqual(router.dequeue_message(), "high")
        self.assertEqual(router.dequeue_message(), "low")

if __name__ == "__main__":
    unittest.main()
