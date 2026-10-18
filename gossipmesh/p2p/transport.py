import logging
import json
import asyncio
from typing import List, Any, Callable, Dict, Optional
from gossipmesh.p2p.fanout import AdaptiveFanoutController
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig, RateLimitMetrics

logger = logging.getLogger(__name__)

class TransportTelemetry:
    def __init__(self):
        self.messages_sent = 0
        self.messages_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self.dropped_messages = 0

class GossipTransport:
    """Manages peer-to-peer transport layer with adaptive fanout controls and rate limiting."""
    def __init__(
        self,
        node_id: str,
        initial_fanout: int = 6,
        config: Optional[RateLimitConfig] = None,
    ):
        self.node_id = node_id
        self.fanout_controller = AdaptiveFanoutController(initial_fanout=initial_fanout)
        self.config = config or RateLimitConfig()
        self.rate_limiter = PeerRateLimiter(self.config)
        self.telemetry = TransportTelemetry()
        self._handlers: Dict[str, List[Callable[[Any], Any]]] = {}

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)

    async def send_payload(self, peer_id: str, payload: Any) -> bool:
        self.telemetry.messages_sent += 1
        serialized = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
        self.telemetry.bytes_sent += len(serialized.encode('utf-8'))
        logger.debug(f"Node {self.node_id} sent payload to peer {peer_id}")
        return True

    async def receive_payload(self, peer_id: str, raw_payload: Any) -> Optional[Any]:
        if not self.rate_limiter.acquire(peer_id):
            self.telemetry.dropped_messages += 1
            logger.warning(f"Rate limit exceeded for peer {peer_id}, dropping message.")
            return None

        self.telemetry.messages_received += 1
        if isinstance(raw_payload, bytes):
            raw_payload = raw_payload.decode('utf-8')
        
        parsed: Any
        if isinstance(raw_payload, str):
            self.telemetry.bytes_received += len(raw_payload.encode('utf-8'))
            try:
                parsed = json.loads(raw_payload)
            except json.JSONDecodeError:
                parsed = raw_payload
        else:
            parsed = raw_payload

        # Dispatch to handlers if topic/type present
        topic = "chat"
        if isinstance(parsed, dict):
            topic = parsed.get("topic", parsed.get("type", "chat"))

        if topic in self._handlers:
            for handler in self._handlers[topic]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(parsed)
                    else:
                        handler(parsed)
                except Exception as e:
                    logger.error(f"Error in handler for topic {topic}: {e}")
                    raise

        return parsed

    def select_peers(self, all_peers: List[str], is_duplicate: bool = False) -> List[str]:
        current_fanout = self.fanout_controller.record_message(is_duplicate=is_duplicate)
        import random
        selected = random.sample(all_peers, min(len(all_peers), current_fanout))
        logger.debug(f"Node {self.node_id} selected {len(selected)} peers with fanout {current_fanout}")
        return selected
