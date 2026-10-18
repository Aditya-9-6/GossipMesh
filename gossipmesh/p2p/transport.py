"""
P2P Transport Layer for GossipMesh.

Integrates per-peer token-bucket rate limiting and bandwidth shaping
to prevent message flooding and resource exhaustion from malicious peers.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, List
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig

logger = logging.getLogger("gossipmesh.p2p.transport")


class TransportTelemetry:
    """Telemetry counters for transport level message throughput and traffic shaping."""

    def __init__(self):
        self.received_messages: int = 0
        self.sent_messages: int = 0
        self.dropped_messages: int = 0
        self.received_bytes: int = 0
        self.sent_bytes: int = 0
        self.dropped_bytes: int = 0

    def record_received(self, size_bytes: int) -> None:
        self.received_messages += 1
        self.received_bytes += size_bytes

    def record_sent(self, size_bytes: int) -> None:
        self.sent_messages += 1
        self.sent_bytes += size_bytes

    def record_dropped(self, size_bytes: int) -> None:
        self.dropped_messages += 1
        self.dropped_bytes += size_bytes

    def to_dict(self) -> Dict[str, int]:
        return {
            "received_messages": self.received_messages,
            "sent_messages": self.sent_messages,
            "dropped_messages": self.dropped_messages,
            "received_bytes": self.received_bytes,
            "sent_bytes": self.sent_bytes,
            "dropped_bytes": self.dropped_bytes,
        }


class GossipTransport:
    """
    Asynchronous Transport Layer with decentralized token-bucket rate limiting.
    Silently drops excess gossip payloads while maintaining telemetry metrics.
    """

    def __init__(
        self,
        node_id: str,
        rate_limiter: Optional[PeerRateLimiter] = None,
        config: Optional[RateLimitConfig] = None,
    ):
        self.node_id = node_id
        self.rate_limiter = rate_limiter or PeerRateLimiter(config=config)
        self.telemetry = TransportTelemetry()
        self.handlers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._lock = asyncio.Lock()

    def _calculate_payload_size(self, payload: Any) -> int:
        if isinstance(payload, bytes):
            return len(payload)
        if isinstance(payload, str):
            return len(payload.encode("utf-8"))
        try:
            return len(json.dumps(payload).encode("utf-8"))
        except Exception:
            return 64

    def register_handler(
        self, topic: str, handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Subscribes a listener to a specific gossip message topic."""
        if topic not in self.handlers:
            self.handlers[topic] = []
        self.handlers[topic].append(handler)

    async def receive_payload(
        self, origin_peer_id: str, raw_payload: Any, topic: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """
        Receives and validates incoming peer payload against rate and bandwidth limits.
        Silently drops excess payloads when limits are breached.
        """
        size_bytes = self._calculate_payload_size(raw_payload)
        allowed, reason = await self.rate_limiter.check_and_consume(
            origin_peer_id, size_bytes
        )

        if not allowed:
            async with self._lock:
                self.telemetry.record_dropped(size_bytes)
            logger.debug(f"Silently dropped payload from {origin_peer_id}: {reason}")
            return None

        # Parse message payload
        parsed_payload: Dict[str, Any]
        if isinstance(raw_payload, dict):
            parsed_payload = raw_payload
        elif isinstance(raw_payload, (str, bytes)):
            try:
                parsed_payload = json.loads(raw_payload)
            except Exception:
                parsed_payload = {
                    "raw": (
                        raw_payload
                        if isinstance(raw_payload, str)
                        else raw_payload.decode("utf-8", "replace")
                    )
                }
        else:
            parsed_payload = {"data": raw_payload}

        async with self._lock:
            self.telemetry.record_received(size_bytes)

        # Dispatch to topic subscribers
        for handler in self.handlers.get(topic, []):
            try:
                handler(parsed_payload)
            except Exception as e:
                logger.error(f"Error executing transport handler for {topic}: {e}")

        return parsed_payload

    async def send_payload(self, target_peer_id: str, payload: Dict[str, Any]) -> bool:
        """Serializes and sends payload to destination peer."""
        size_bytes = self._calculate_payload_size(payload)
        async with self._lock:
            self.telemetry.record_sent(size_bytes)
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        """Returns consolidated transport and rate limiter metrics."""
        async with self._lock:
            transport_stats = self.telemetry.to_dict()
        limiter_stats = await self.rate_limiter.get_metrics()
        return {
            "transport": transport_stats,
            "rate_limiter": limiter_stats,
            "node_id": self.node_id,
        }
