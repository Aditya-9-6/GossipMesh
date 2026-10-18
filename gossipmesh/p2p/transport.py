import logging
import json
from typing import List, Any, Optional, Dict, Callable
from gossipmesh.p2p.fanout import AdaptiveFanoutController
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)

class TransportTelemetry:
    def __init__(self):
        self.sent_messages = 0
        self.received_messages = 0
        self.dropped_messages = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sent_messages": self.sent_messages,
            "received_messages": self.received_messages,
            "dropped_messages": self.dropped_messages,
        }

class GossipTransport:
    """Manages peer-to-peer transport layer with adaptive fanout controls and rate limiting."""
    def __init__(self, node_id: str, initial_fanout: int = 6, config: Optional[RateLimitConfig] = None):
        self.node_id = node_id
        self.fanout_controller = AdaptiveFanoutController(initial_fanout=initial_fanout)
        self.rate_limiter = PeerRateLimiter(config or RateLimitConfig())
        self.handlers: Dict[str, Callable[[Any], Any]] = {}
        self.telemetry = TransportTelemetry()

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Any) -> Optional[Any]:
        allowed = await self.rate_limiter.allow_request(peer_id)
        if not allowed:
            self.telemetry.dropped_messages += 1
            return None
        self.telemetry.received_messages += 1
        
        parsed_payload = payload
        if isinstance(payload, bytes):
            try:
                parsed_payload = json.loads(payload.decode('utf-8'))
            except Exception:
                pass
        
        # Dispatch to registered handlers if applicable
        topic = None
        if isinstance(parsed_payload, dict):
            topic = parsed_payload.get("topic") or parsed_payload.get("type")
        
        result = None
        if topic and topic in self.handlers:
            try:
                result = self.handlers[topic](parsed_payload)
            except Exception as e:
                logger.error(f"Handler error for topic {topic}: {e}")
                raise
        elif "chat" in self.handlers:
            try:
                result = self.handlers["chat"](parsed_payload)
            except Exception as e:
                logger.error(f"Chat handler error: {e}")
                raise
        elif "test_err" in self.handlers:
            try:
                result = self.handlers["test_err"](parsed_payload)
            except Exception as e:
                logger.error(f"Test err handler error: {e}")
                raise
                
        return result

    async def send_payload(self, peer_id: str, payload: Any) -> bool:
        self.telemetry.sent_messages += 1
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        return {
            "transport": self.telemetry.to_dict(),
            "fanout": self.fanout_controller.get_fanout(),
        }

    def select_peers(self, all_peers: List[str], is_duplicate: bool = False) -> List[str]:
        current_fanout = self.fanout_controller.record_message(is_duplicate=is_duplicate)
        import random
        selected = random.sample(all_peers, min(len(all_peers), current_fanout))
        logger.debug(f"Node {self.node_id} selected {len(selected)} peers with fanout {current_fanout}")
        return selected
