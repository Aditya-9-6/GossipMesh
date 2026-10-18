import logging
import json
from typing import List, Any, Optional, Dict, Callable
from gossipmesh.p2p.fanout import AdaptiveFanoutController
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)

class TransportTelemetry:
    def __init__(self):
        self.sent_messages = 0
        self.sent_bytes = 0
        self.received_messages = 0
        self.received_bytes = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sent_messages": self.sent_messages,
            "sent_bytes": self.sent_bytes,
            "received_messages": self.received_messages,
            "received_bytes": self.received_bytes,
        }

class GossipTransport:
    """Manages peer-to-peer transport layer with adaptive fanout controls and rate limiting."""
    def __init__(self, node_id: str, initial_fanout: int = 6, config: Optional[RateLimitConfig] = None):
        self.node_id = node_id
        self.fanout_controller = AdaptiveFanoutController(initial_fanout=initial_fanout)
        self.rate_limiter = PeerRateLimiter(config=config or RateLimitConfig())
        self.handlers: Dict[str, List[Callable[[Any], Any]]] = {}
        self.telemetry = TransportTelemetry()

    def register_handler(self, topic: str, handler: Callable[[Any], Any]):
        if topic not in self.handlers:
            self.handlers[topic] = []
        self.handlers[topic].append(handler)

    def select_peers(self, all_peers: List[str], is_duplicate: bool = False) -> List[str]:
        current_fanout = self.fanout_controller.record_message(is_duplicate=is_duplicate)
        import random
        selected = random.sample(all_peers, min(len(all_peers), current_fanout))
        logger.debug(f"Node {self.node_id} selected {len(selected)} peers with fanout {current_fanout}")
        return selected

    async def send_payload(self, peer_id: str, payload: Any) -> bool:
        payload_bytes = json.dumps(payload).encode('utf-8') if not isinstance(payload, bytes) else payload
        self.telemetry.sent_messages += 1
        self.telemetry.sent_bytes += len(payload_bytes)
        return True

    async def receive_payload(self, peer_id: str, payload: Any, topic: Optional[str] = None) -> Optional[Any]:
        allowed = await self.rate_limiter.check_rate_limit(peer_id)
        if not allowed:
            return None

        payload_bytes = json.dumps(payload).encode('utf-8') if not isinstance(payload, bytes) else payload
        self.telemetry.received_messages += 1
        self.telemetry.received_bytes += len(payload_bytes)

        if topic and topic in self.handlers:
            for handler in self.handlers[topic]:
                try:
                    if callable(handler):
                        handler(payload)
                except Exception as e:
                    logger.error(f"Error in handler for topic {topic}: {e}")

        return payload

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        return {
            "transport": self.telemetry.to_dict(),
            "rate_limiter": self.rate_limiter.get_metrics()
        }
