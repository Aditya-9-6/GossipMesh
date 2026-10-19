"""
Gossip Message Priority Router and P2P Router.

Classifies incoming and outgoing gossip protocol packets and delegates them
to multi-level weighted priority queues to isolate control-plane heartbeats
from bulky data-plane replication traffic, alongside PlumTree mesh routing.
"""

import threading
import uuid
from typing import Any, Callable, Dict, List, Optional

from gossipmesh.p2p.plumtree import PlumTreeMesh
from gossipmesh.p2p.priority_queue import (
    MessagePriority,
    PrioritizedMessage,
    PriorityQueueConfig,
    WeightedPriorityQueue,
)


class P2PRouter:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.mesh = PlumTreeMesh(node_id)

    def register_peer(self, peer_id: str, eager: bool = True) -> None:
        if eager:
            self.mesh.add_eager_peer(peer_id)
        else:
            self.mesh.add_lazy_peer(peer_id)

    def unregister_peer(self, peer_id: str) -> None:
        self.mesh.remove_peer(peer_id)

    def route_message(self, message_id: str, payload: Any, from_peer: str) -> Dict[str, Any]:
        is_duplicate = self.mesh.handle_message(message_id, payload, from_peer)
        
        # Determine forwarding targets
        eager_targets = self.mesh.get_eager_peers()
        if from_peer in eager_targets:
            eager_targets.remove(from_peer)

        lazy_targets = self.mesh.get_lazy_peers()
        if from_peer in lazy_targets:
            lazy_targets.remove(from_peer)

        return {
            "is_duplicate": is_duplicate,
            "forward_eager": eager_targets,
            "forward_lazy": lazy_targets,
        }


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
