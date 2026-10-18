import logging
import json
import time
from typing import List, Any, Optional, Callable, Dict
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "dropped_messages": self.dropped_messages,
        }


class GossipTransport:
    """Manages peer-to-peer transport layer with adaptive fanout controls, rate limiting, and handlers."""
    def __init__(
        self,
        node_id: str,
        initial_fanout: int = 6,
        config: Optional[RateLimitConfig] = None,
    ):
        self.node_id = node_id
        self.fanout_controller = AdaptiveFanoutController(initial_fanout=initial_fanout)
        self.rate_limiter = PeerRateLimiter(config=config or RateLimitConfig())
        self.handlers: Dict[str, List[Callable[[Any], Any]]] = {}
        self.telemetry = TransportTelemetry()

    def register_handler(self, topic: str, callback: Callable[[Any], Any]) -> None:
        if topic not in self.handlers:
            self.handlers[topic] = []
        self.handlers[topic].append(callback)

    async def receive_payload(
        self, peer_id: str, raw_payload: Any, topic: Optional[str] = None
    ) -> Optional[Any]:
        if not self.rate_limiter.acquire(peer_id):
            self.telemetry.dropped_messages += 1
            logger.warning(f"Rate limit exceeded for peer {peer_id}. Message dropped.")
            return None

        self.telemetry.messages_received += 1

        payload = raw_payload
        if isinstance(raw_payload, bytes):
            try:
                payload = json.loads(raw_payload.decode('utf-8'))
            except Exception:
                pass
        elif isinstance(raw_payload, str):
            try:
                payload = json.loads(raw_payload)
            except Exception:
                pass

        if isinstance(payload, dict) and not topic:
            topic = payload.get("topic")

        results = []
        if topic and topic in self.handlers:
            for cb in self.handlers[topic]:
                try:
                    res = cb(payload)
                    if hasattr(res, "__await__"):
                        res = await res
                    results.append(res)
                except Exception as e:
                    logger.error(f"Error in handler for topic {topic}: {e}")

        return results[0] if len(results) == 1 else (results if results else payload)

    async def send_payload(self, peer_id: str, payload: Any, topic: Optional[str] = None) -> bool:
        self.telemetry.messages_sent += 1
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        return self.telemetry.to_dict()

    def select_peers(self, all_peers: List[str], is_duplicate: bool = False) -> List[str]:
        current_fanout = self.fanout_controller.record_message(is_duplicate=is_duplicate)
        import random
        selected = random.sample(all_peers, min(len(all_peers), current_fanout))
        logger.debug(f"Node {self.node_id} selected {len(selected)} peers with fanout {current_fanout}")
        return selected
