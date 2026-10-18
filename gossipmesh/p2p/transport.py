import logging
import asyncio
import json
from typing import List, Any, Dict, Optional
from gossipmesh.p2p.fanout import AdaptiveFanoutController
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)

class TransportTelemetry:
    def __init__(self):
        self.packets_sent = 0
        self.packets_received = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_received,
        }

class GossipTransport:
    """Manages peer-to-peer transport layer with adaptive fanout controls and rate limiting."""
    def __init__(self, node_id: str, initial_fanout: int = 6, config: Optional[RateLimitConfig] = None):
        self.node_id = node_id
        self.fanout_controller = AdaptiveFanoutController(initial_fanout=initial_fanout)
        self.rate_limiter = PeerRateLimiter(config=config or RateLimitConfig())
        self.telemetry = TransportTelemetry()

    def select_peers(self, all_peers: List[str], is_duplicate: bool = False) -> List[str]:
        current_fanout = self.fanout_controller.record_message(is_duplicate=is_duplicate)
        import random
        selected = random.sample(all_peers, min(len(all_peers), current_fanout))
        logger.debug(f"Node {self.node_id} selected {len(selected)} peers with fanout {current_fanout}")
        return selected

    async def receive_payload(self, peer_id: str, payload: Any) -> Optional[Any]:
        allowed = await self.rate_limiter.acquire(peer_id)
        if not allowed:
            return None
        self.telemetry.packets_received += 1
        
        if isinstance(payload, bytes):
            try:
                return json.loads(payload.decode('utf-8'))
            except Exception:
                return payload.decode('utf-8', errors='ignore')
        elif isinstance(payload, str):
            try:
                return json.loads(payload)
            except Exception:
                return {"raw": payload}
        return payload

    async def send_payload(self, peer_id: str, payload: Any) -> bool:
        self.telemetry.packets_sent += 1
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        metrics_obj = self.rate_limiter.get_metrics()
        if asyncio.iscoroutine(metrics_obj):
            metrics_obj = await metrics_obj
        
        rate_limiter_dict = metrics_obj.to_dict() if hasattr(metrics_obj, "to_dict") else dict(metrics_obj)
        return {
            "transport": self.telemetry.to_dict(),
            "rate_limiter": rate_limiter_dict
        }
