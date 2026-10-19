"""
Unit test suite for GossipMesh P2P Weighted Priority Queue and Message Router.
"""

import threading
import time
import unittest
import pytest
from gossipmesh.p2p.priority_queue import (
    MessagePriority,
    PriorityQueueConfig,
    WeightedPriorityQueue,
    PriorityQueueMessage,
)
from gossipmesh.p2p.router import GossipMessageRouter, GossipRouter


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


class TestMessagePriorityOrdering:
    def test_priority_hierarchy(self):
        assert MessagePriority.CONTROL < MessagePriority.HIGH
        assert MessagePriority.HIGH < MessagePriority.NORMAL
        assert MessagePriority.NORMAL < MessagePriority.LOW


class TestWeightedPriorityQueue:
    def test_control_plane_precedence(self):
        queue = WeightedPriorityQueue()
        # Enqueue normal and low messages first
        queue.enqueue("norm1", "payload_normal", priority=MessagePriority.NORMAL)
        queue.enqueue("low1", "payload_low", priority=MessagePriority.LOW)
        # Enqueue control message after
        queue.enqueue("ctrl1", "heartbeat", priority=MessagePriority.CONTROL)

        # Control message must be scheduled first
        msg1 = queue.dequeue()
        assert msg1 is not None
        assert msg1.message_id == "ctrl1"
        assert msg1.base_priority == MessagePriority.CONTROL

    def test_fifo_within_same_priority(self):
        queue = WeightedPriorityQueue()
        queue.enqueue("p1", "first", priority=MessagePriority.HIGH)
        queue.enqueue("p2", "second", priority=MessagePriority.HIGH)
        queue.enqueue("p3", "third", priority=MessagePriority.HIGH)

        assert queue.dequeue().message_id == "p1"
        assert queue.dequeue().message_id == "p2"
        assert queue.dequeue().message_id == "p3"

    def test_capacity_rejection(self):
        config = PriorityQueueConfig(max_capacity=2)
        queue = WeightedPriorityQueue(config=config)

        assert queue.enqueue("m1", "val1") is True
        assert queue.enqueue("m2", "val2") is True
        assert queue.size() == 2

        # Exceed capacity
        assert queue.enqueue("m3", "val3") is False
        assert queue.size() == 2
        metrics = queue.get_metrics()
        assert metrics["total_dropped"] == 1

    def test_input_validation(self):
        queue = WeightedPriorityQueue()
        with pytest.raises(ValueError, match="empty"):
            queue.enqueue("", "payload")
        with pytest.raises(ValueError, match="positive"):
            queue.enqueue("m1", "payload", size_bytes=0)
        with pytest.raises(ValueError, match="positive"):
            queue.enqueue("m1", "payload", size_bytes=-10)

    def test_anti_starvation_aging(self):
        # Configure short aging interval (0.05s)
        config = PriorityQueueConfig(aging_interval_sec=0.05, enable_aging=True)
        queue = WeightedPriorityQueue(config=config)

        t0 = time.monotonic()
        queue.enqueue("low_msg", "data", priority=MessagePriority.LOW, now=t0)
        assert queue.peek().effective_priority == MessagePriority.LOW.value

        # Advance simulated time past aging interval
        t1 = t0 + 0.06
        promoted = queue.apply_aging(now=t1)
        assert promoted == 1

        msg = queue.peek()
        # Promoted from LOW (3) -> NORMAL (2)
        assert msg.effective_priority == MessagePriority.NORMAL.value
        assert msg.promotions == 1

        # Second promotion past another interval -> HIGH (1)
        t2 = t1 + 0.06
        queue.apply_aging(now=t2)
        assert queue.peek().effective_priority == MessagePriority.HIGH.value
        assert queue.peek().promotions == 2

    def test_peek_and_empty_behavior(self):
        queue = WeightedPriorityQueue()
        assert queue.is_empty() is True
        assert queue.dequeue() is None
        assert queue.peek() is None

        queue.enqueue("m1", "payload", priority=MessagePriority.NORMAL)
        assert queue.is_empty() is False
        assert queue.peek().message_id == "m1"
        assert queue.size() == 1

        queue.clear()
        assert queue.is_empty() is True
        assert queue.size() == 0

    def test_metrics_reporting(self):
        queue = WeightedPriorityQueue()
        queue.enqueue("m1", "p1", priority=MessagePriority.CONTROL)
        queue.enqueue("m2", "p2", priority=MessagePriority.NORMAL)
        queue.dequeue()

        metrics = queue.get_metrics()
        assert metrics["total_enqueued"] == 2
        assert metrics["total_dequeued"] == 1
        assert metrics["total_size"] == 1
        assert metrics["level_counts"]["NORMAL"] == 1
        assert metrics["level_counts"]["CONTROL"] == 0


class TestGossipMessageRouter:
    def test_type_classification(self):
        router = GossipMessageRouter()
        assert router.classify_priority("heartbeat") == MessagePriority.CONTROL
        assert router.classify_priority("ping") == MessagePriority.CONTROL
        assert router.classify_priority("digest") == MessagePriority.HIGH
        assert router.classify_priority("event") == MessagePriority.NORMAL
        assert router.classify_priority("telemetry") == MessagePriority.LOW
        # Unknown falls back to NORMAL
        assert router.classify_priority("custom_unknown_action") == MessagePriority.NORMAL

    def test_priority_override(self):
        router = GossipMessageRouter()
        router.set_priority_override("custom_alert", MessagePriority.CONTROL)
        assert router.classify_priority("custom_alert") == MessagePriority.CONTROL

    def test_route_and_dequeue(self):
        router = GossipMessageRouter()
        ok = router.route_outgoing("event", {"value": 42}, message_id="ev_001")
        assert ok is True

        msg = router.get_next_outgoing()
        assert msg is not None
        assert msg.message_id == "ev_001"
        assert msg.payload == {"value": 42}
        assert msg.base_priority == MessagePriority.NORMAL

    def test_invalid_outgoing_type(self):
        router = GossipMessageRouter()
        with pytest.raises(ValueError, match="empty"):
            router.route_outgoing("", {"data": 1})

    def test_incoming_dispatch(self):
        router = GossipMessageRouter()
        handled_events = []

        def handle_heartbeat(payload):
            handled_events.append(payload)
            return "ok"

        router.register_handler("heartbeat", handle_heartbeat)
        result = router.dispatch_incoming("heartbeat", {"node_id": "peer_1"})

        assert result == "ok"
        assert len(handled_events) == 1
        assert handled_events[0] == {"node_id": "peer_1"}

    def test_unregistered_handler_raises(self):
        router = GossipMessageRouter()
        with pytest.raises(KeyError, match="No registered handler"):
            router.dispatch_incoming("unknown_topic", {})

    def test_telemetry(self):
        router = GossipMessageRouter()
        router.register_handler("ping", lambda p: "pong")
        router.dispatch_incoming("ping", {})

        telemetry = router.get_telemetry()
        assert telemetry["dispatched_incoming"] == 1
        assert "ping" in telemetry["registered_handlers"]
        assert "queue" in telemetry


class TestSchedulingLatencyAndConcurrency:
    def test_scheduling_latency_bound(self):
        queue = WeightedPriorityQueue()
        # Measure scheduling overhead of 1000 enqueues and dequeues
        t0 = time.perf_counter()
        for i in range(1000):
            queue.enqueue(f"msg_{i}", f"payload_{i}", priority=MessagePriority(i % 4))
        for _ in range(1000):
            queue.dequeue()
        total_time = time.perf_counter() - t0
        avg_overhead_ms = (total_time / 2000) * 1000.0

        # Must strictly be well below 5ms bound (typically <0.01ms in O(1))
        assert avg_overhead_ms < 5.0

    def test_concurrent_enqueue_dequeue(self):
        queue = WeightedPriorityQueue(config=PriorityQueueConfig(max_capacity=5000))
        errors = []

        def producer(thread_id: int):
            try:
                for i in range(50):
                    queue.enqueue(
                        f"t{thread_id}_m{i}",
                        f"payload_{i}",
                        priority=MessagePriority(i % 4),
                    )
                    time.sleep(0.0005)
            except Exception as e:
                errors.append(e)

        def consumer():
            try:
                for _ in range(100):
                    queue.dequeue()
                    time.sleep(0.0005)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=producer, args=(1,)),
            threading.Thread(target=producer, args=(2,)),
            threading.Thread(target=consumer),
            threading.Thread(target=consumer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        metrics = queue.get_metrics()
        assert metrics["total_enqueued"] == 100


if __name__ == "__main__":
    unittest.main()
