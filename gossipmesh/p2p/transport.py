import logging
import time
from typing import List, Any, Dict, Optional, Callable
from gossipmesh.p2p.fanout import AdaptiveFanoutController
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)

class TransportTelemetry:
    def __init__(self):
        self.sent_messages = 0
        self.received_messages = 0
        self.dropped_messages = 0

class GossipTransport:
    """Manages peer-to-peer transport layer with adaptive fanout controls and rate limiting."""
    def __init__(self, node_id: str, initial_fanout: int = 6, config: Optional[RateLimitConfig] = None):
        self.node_id = node_id
        self.fanout_controller = AdaptiveFanoutController(initial_fanout=initial_fanout)
        self.rate_limiter = PeerRateLimiter(config=config)
        self.telemetry = TransportTelemetry()
        self.handlers: Dict[str, Callable[[Any], None]] = {}

    def register_handler(self, topic: str, handler: Callable[[Any], None]) -> None:
        self.handlers[topic] = handler

    def select_peers(self, all_peers: List[str], is_duplicate: bool = False) -> List[str]:
        current_fanout = self.fanout_controller.record_message(is_duplicate=is_duplicate)
        import random
        selected = random.sample(all_peers, min(len(all_peers), current_fanout))
        logger.debug(f"Node {self.node_id} selected {len(selected)} peers with fanout {current_fanout}")
        return selected

    async def send_payload(self, peer_id: str, payload: Any, topic: Optional[str] = None) -> bool:
        self.telemetry.sent_messages += 1
        return True

    async def receive_payload(
        self, peer_id: str, raw_payload: Any, topic: Optional[str] = None
    ) -> Optional[Any]:
        # Estimate size or default to 1
        size_bytes = len(str(raw_payload))
        if not self.rate_limiter.check_and_consume(peer_id, size_bytes=size_bytes):
            self.telemetry.dropped_messages += 1
            return None

        self.telemetry.received_messages += 1
        payload = raw_payload
        if topic and topic in self.handlers:
            try:
                handler = self.handlers[topic]
                if callable(handler):
                    handler(payload)
            except Exception as e:
                logger.error(f"Error in handler for topic {topic}: {e}")
        return payload

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        return {
            "transport": {
                "sent_messages": self.telemetry.sent_messages,
                "received_messages": self.telemetry.received_messages,
                "dropped_messages": self.telemetry.dropped_messages,
            },
            "node_id": self.node_id,
        }
