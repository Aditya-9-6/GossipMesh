import time
import uuid
from typing import Dict, Any, Optional

class EntropyControlFrame:
    def __init__(self, sender_id: str, vector_clock: Dict[str, int], merkle_digest: str, message_id: Optional[str] = None, timestamp: Optional[float] = None):
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
    def from_dict(cls, data: Dict[str, Any]) -> 'EntropyControlFrame':
        return cls(
            sender_id=data["sender_id"],
            vector_clock=data["vector_clock"],
            merkle_digest=data["merkle_digest"],
            message_id=data.get("message_id"),
            timestamp=data.get("timestamp"),
        )
