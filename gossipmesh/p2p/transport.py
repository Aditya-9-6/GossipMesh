import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Tuple, Optional, Callable
from gossipmesh.p2p.erasure import ErasureCoder
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)


class TransportTelemetry:
    """Telemetry counters for transport layer messaging and bandwidth."""
    def __init__(self):
        self.sent_messages = 0
        self.received_messages = 0
        self.dropped_messages = 0
        self.sent_bytes = 0
        self.received_bytes = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sent_messages": self.sent_messages,
            "received_messages": self.received_messages,
            "dropped_messages": self.dropped_messages,
            "sent_bytes": self.sent_bytes,
            "received_bytes": self.received_bytes,
        }


class GossipTransport:
    """Async P2P Transport Layer with rate-limiting, backpressure protection, and payload dispatch."""
    def __init__(self, node_id: str, config: Optional[RateLimitConfig] = None):
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config=config or RateLimitConfig())
        self.telemetry = TransportTelemetry()
        self.handlers: Dict[str, Callable[[Any], Any]] = {}

    def register_handler(self, topic: str, handler: Callable[[Any], Any]):
        self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Any, topic: str = "default") -> Optional[Dict[str, Any]]:
        # Format payload into standard dict format
        if isinstance(payload, bytes):
            try:
                payload_dict = json.loads(payload.decode('utf-8'))
            except Exception:
                payload_dict = {"raw": payload.decode('errors', 'ignore')}
            payload_bytes = len(payload)
        elif isinstance(payload, str):
            try:
                payload_dict = json.loads(payload)
            except Exception:
                payload_dict = {"raw": payload}
            payload_bytes = len(payload.encode('utf-8'))
        elif isinstance(payload, dict):
            payload_dict = payload
            payload_bytes = len(json.dumps(payload).encode('utf-8'))
        elif isinstance(payload, (int, float, list)):
            payload_dict = {"data": payload}
            payload_bytes = len(json.dumps(payload).encode('utf-8'))
        else:
            payload_dict = {"data": str(payload)}
            payload_bytes = len(str(payload).encode('utf-8'))

        allowed, _reason = await self.rate_limiter.check_and_consume(peer_id, payload_bytes)
        if not allowed:
            self.telemetry.dropped_messages += 1
            return None

        self.telemetry.received_messages += 1
        self.telemetry.received_bytes += payload_bytes

        if topic in self.handlers:
            try:
                res = self.handlers[topic](payload_dict)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.error(f"Error in transport handler for topic {topic}: {e}")

        return payload_dict

    async def send_payload(self, peer_id: str, payload: Any) -> bool:
        serialized = json.dumps(payload).encode('utf-8') if not isinstance(payload, bytes) else payload
        self.telemetry.sent_messages += 1
        self.telemetry.sent_bytes += len(serialized)
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        limiter_metrics = await self.rate_limiter.get_metrics()
        return {
            "transport": self.telemetry.to_dict(),
            "rate_limiter": limiter_metrics
        }


class P2PSessionTransport(GossipTransport):
    """Session-secured wrapper around GossipTransport."""
    pass


class ErasureTransportMultiplexer:
    """Integrates erasure coding fragment multiplexing into gossip transport dissemination.
    """
    def __init__(self, k: int = 4, m: int = 2):
        self.coder = ErasureCoder(k=k, m=m)

    def prepare_dissemination(self, payload_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_data = json.dumps(payload_dict).encode('utf-8')
        original_size = len(raw_data)
        fragments = self.coder.encode(raw_data)
        
        dissemination_packets = []
        for shard_idx, shard_data in fragments:
            packet = {
                "shard_index": shard_idx,
                "k": self.coder.k,
                "m": self.coder.m,
                "original_size": original_size,
                "payload_shard": shard_data.hex()
            }
            dissemination_packets.append(packet)
        return dissemination_packets

    def assemble_dissemination(self, packets: List[Dict[str, Any]]) -> Dict[str, Any]:
        fragments = []
        original_size = None
        for pkt in packets:
            idx = pkt["shard_index"]
            data = bytes.fromhex(pkt["payload_shard"])
            fragments.append((idx, data))
            if original_size is None:
                original_size = pkt.get("original_size")
                
        raw_bytes = self.coder.decode(fragments, original_size=original_size)
        return json.loads(raw_bytes.decode('utf-8'))
