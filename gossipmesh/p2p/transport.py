import logging
from typing import List, Any, Optional, Callable, Dict
from gossipmesh.p2p.fanout import AdaptiveFanoutController
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)

class TransportTelemetry:
    def __init__(self):
        self.sent_messages = 0
        self.sent_bytes = 0
        self.received_messages = 0
        self.received_bytes = 0
        self.dropped_messages = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sent_messages": self.sent_messages,
            "sent_bytes": self.sent_bytes,
            "received_messages": self.received_messages,
            "received_bytes": self.received_bytes,
            "dropped_messages": self.dropped_messages,
        }

class GossipTransport:
    """Manages peer-to-peer transport layer with adaptive fanout controls and rate limiting."""
    def __init__(self, node_id: str, initial_fanout: int = 6, config: Optional[RateLimitConfig] = None):
        self.node_id = node_id
        self.fanout_controller = AdaptiveFanoutController(initial_fanout=initial_fanout)
        self.rate_limiter = PeerRateLimiter(config=config or RateLimitConfig())
        self.handlers: Dict[str, List[Callable[[Any], Any]]] = {}
        self.telemetry = TransportTelemetry()

    def select_peers(self, all_peers: List[str], is_duplicate: bool = False) -> List[str]:
        current_fanout = self.fanout_controller.record_message(is_duplicate=is_duplicate)
        import random
        selected = random.sample(all_peers, min(len(all_peers), current_fanout))
        logger.debug(f"Node {self.node_id} selected {len(selected)} peers with fanout {current_fanout}")
        return selected

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        if topic not in self.handlers:
            self.handlers[topic] = []
        self.handlers[topic].append(handler)

    async def send_payload(self, peer_id: str, payload: Any) -> bool:
        serialized = str(payload).encode('utf-8') if isinstance(payload, (dict, list, str)) else bytes(payload)
        b_len = len(serialized)
        self.telemetry.sent_messages += 1
        self.telemetry.sent_bytes += b_len
        logger.debug(f"Node {self.node_id} sent payload to {peer_id} ({b_len} bytes)")
        return True

    async def receive_payload(
        self, peer_id: str, raw_payload: Any, topic: Optional[str] = None
    ) -> Optional[Any]:
        size_bytes = len(str(raw_payload))
        self.telemetry.received_bytes += size_bytes
        self.telemetry.received_messages += 1

        if not self.rate_limiter.check_and_consume(peer_id):
            self.telemetry.dropped_messages += 1
            logger.warning(f"Node {self.node_id} rate-limited and dropped payload from {peer_id}")
            return None

        if topic and topic in self.handlers:
            for handler in self.handlers[topic]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(raw_payload)
                    else:
                        handler(raw_payload)
                except Exception as e:
                    logger.error(f"Error in handler for topic {topic}: {e}")

        return raw_payload

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        return {
            "transport": self.telemetry.to_dict(),
            "rate_limiter": self.rate_limiter.get_metrics().to_dict()
        }
