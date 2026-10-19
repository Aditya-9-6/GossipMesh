import time
import uuid
from typing import Dict, Any, Optional


class EntropyControlFrame:
    def __init__(
        self,
        sender_id: str,
        vector_clock: Dict[str, int],
        merkle_digest: str,
        message_id: Optional[str] = None,
        timestamp: Optional[float] = None,
    ):
        self.sender_id = sender_id
        self.vector_clock = vector_clock
        self.merkle_digest = merkle_digest
        self.message_id = message_id or str(uuid.uuid4())
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender_id": self.sender_id,
            "vector_clock": self.vector_clock,
            "merkle_digest": self.merkle_digest,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntropyControlFrame":
        return cls(
            sender_id=data["sender_id"],
            vector_clock=data["vector_clock"],
            merkle_digest=data["merkle_digest"],
            message_id=data.get("message_id"),
            timestamp=data.get("timestamp"),
        )


class GossipProtocolHandler:
    """Protocol handler managing message deduplication, retransmission, and backpressure."""

    def __init__(self, capacity: int = 100, max_memory_bytes: int = 1024 * 1024):
        from gossipmesh.p2p.retransmit import RetransmissionCache

        self.cache = RetransmissionCache(capacity=capacity, max_memory_bytes=max_memory_bytes)
        self.messages: Dict[str, Any] = {}

    def handle_broadcast(self, message_id: str, payload: Any) -> bool:
        self.messages[message_id] = payload
        return self.cache.put(message_id, payload)

    def request_retransmit(self, message_id: str) -> Optional[Any]:
        return self.cache.get(message_id) or self.messages.get(message_id)

    def is_congested(self) -> bool:
        return self.cache.check_backpressure()
