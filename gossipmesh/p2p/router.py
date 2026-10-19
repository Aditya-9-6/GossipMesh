"""
Gossip Message Priority Router.

Classifies incoming and outgoing gossip protocol packets and delegates them
to multi-level weighted priority queues to isolate control-plane heartbeats
from bulky data-plane replication traffic.
"""

import threading
import uuid
from typing import Any, Callable, Dict, Optional

from gossipmesh.p2p.priority_queue import (
    MessagePriority,
    PrioritizedMessage,
    PriorityQueueConfig,
    WeightedPriorityQueue,
)


class GossipMessageRouter:
    """
    Routes gossip messages according to semantic priority rules and dispatches
    incoming traffic to registered domain handlers.
    """

    DEFAULT_TYPE_PRIORITIES: Dict[str, MessagePriority] = {
        # Control plane signals
        "heartbeat": MessagePriority.CONTROL,
        "ping": MessagePriority.CONTROL,
        "pong": MessagePriority.CONTROL,
        "membership": MessagePriority.CONTROL,
        "consensus": MessagePriority.CONTROL,
        "election": MessagePriority.CONTROL,
        # High-priority state synchronization
        "digest": MessagePriority.HIGH,
        "sync": MessagePriority.HIGH,
        "merkle": MessagePriority.HIGH,
        "anti_entropy": MessagePriority.HIGH,
        # Standard application payloads
        "broadcast": MessagePriority.NORMAL,
        "event": MessagePriority.NORMAL,
        "message": MessagePriority.NORMAL,
        "transaction": MessagePriority.NORMAL,
        # Low-priority background diagnostics
        "telemetry": MessagePriority.LOW,
        "metric": MessagePriority.LOW,
        "log": MessagePriority.LOW,
        "diagnostics": MessagePriority.LOW,
    }

    def __init__(self, queue_config: Optional[PriorityQueueConfig] = None) -> None:
        self.queue = WeightedPriorityQueue(config=queue_config)
        self._type_priorities: Dict[str, MessagePriority] = dict(
            self.DEFAULT_TYPE_PRIORITIES
        )
        self._incoming_handlers: Dict[str, Callable[[Any], Any]] = {}
        self._dispatched_count: int = 0
        self._lock = threading.Lock()

    def classify_priority(self, message_type: str) -> MessagePriority:
        """Determines the message priority for a given message type string."""
        normalized = message_type.lower().strip()
        with self._lock:
            return self._type_priorities.get(normalized, MessagePriority.NORMAL)

    def set_priority_override(
        self, message_type: str, priority: MessagePriority
    ) -> None:
        """Registers a custom priority level for a specific message type."""
        normalized = message_type.lower().strip()
        with self._lock:
            self._type_priorities[normalized] = priority

    def route_outgoing(
        self,
        message_type: str,
        payload: Any,
        message_id: Optional[str] = None,
        priority_override: Optional[MessagePriority] = None,
        size_bytes: int = 1,
    ) -> bool:
        """
        Classifies and schedules an outgoing message into the priority queue.
        """
        if not message_type:
            raise ValueError("message_type cannot be empty")

        msg_id = message_id or str(uuid.uuid4())
        priority = (
            priority_override
            if priority_override is not None
            else self.classify_priority(message_type)
        )
        return self.queue.enqueue(
            message_id=msg_id, payload=payload, priority=priority, size_bytes=size_bytes
        )

    def get_next_outgoing(self) -> Optional[PrioritizedMessage]:
        """Dequeues the next scheduled outgoing message."""
        return self.queue.dequeue()

    def register_handler(
        self, message_type: str, handler: Callable[[Any], Any]
    ) -> None:
        """Registers a callback handler for processing incoming messages of a type."""
        normalized = message_type.lower().strip()
        with self._lock:
            self._incoming_handlers[normalized] = handler

    def dispatch_incoming(self, message_type: str, payload: Any) -> Any:
        """Dispatches an incoming message to its registered domain handler."""
        normalized = message_type.lower().strip()
        with self._lock:
            handler = self._incoming_handlers.get(normalized)

        if handler is None:
            raise KeyError(f"No registered handler for message type: {message_type}")

        with self._lock:
            self._dispatched_count += 1
        return handler(payload)

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns routing and queue telemetry metrics."""
        with self._lock:
            q_metrics = self.queue.get_metrics()
            return {
                "queue": q_metrics,
                "dispatched_incoming": self._dispatched_count,
                "registered_handlers": list(self._incoming_handlers.keys()),
            }
