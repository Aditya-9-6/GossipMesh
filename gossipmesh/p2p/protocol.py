from typing import Dict, Any, Optional
from gossipmesh.p2p.retransmit import RetransmissionCache


class GossipProtocolHandler:
    """Protocol handler integrating retransmission caching and backpressure telemetry."""

    def __init__(self, capacity: int = 1000, max_memory_bytes: int = 16 * 1024 * 1024):
        self.retransmit_cache = RetransmissionCache(capacity=capacity, max_memory_bytes=max_memory_bytes)

    def handle_broadcast(self, message_id: str, payload: Dict[str, Any]) -> bool:
        """Buffers broadcasted message and signals backpressure if threshold reached."""
        success = self.retransmit_cache.put(message_id, payload)
        return success

    def request_retransmit(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Fetches cached message for dropped packet recovery."""
        return self.retransmit_cache.get(message_id)

    def is_congested(self) -> bool:
        """Checks downstream backpressure status."""
        return self.retransmit_cache.check_backpressure()
