import time
import logging
import asyncio
from typing import Dict, Any, Optional, Union, Callable

from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig
from gossipmesh.p2p.reputation import LeakyBucketReputation


class TransportTelemetry:
    def __init__(self) -> None:
        self.sent_messages = 0
        self.sent_bytes = 0
        self.received_messages = 0
        self.received_bytes = 0
        self.dropped_messages = 0

    def record_sent(self, size: int) -> None:
        self.sent_messages += 1
        self.sent_bytes += size

    def record_received(self, size: int) -> None:
        self.received_messages += 1
        self.received_bytes += size

    def record_dropped(self) -> None:
        self.dropped_messages += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sent_messages": self.sent_messages,
            "sent_bytes": self.sent_bytes,
            "received_messages": self.received_messages,
            "received_bytes": self.received_bytes,
            "dropped_messages": self.dropped_messages,
        }


class GossipTransport:
    def __init__(
        self,
        node_id: str,
        config: Optional[RateLimitConfig] = None,
        reputation: Optional[LeakyBucketReputation] = None
    ) -> None:
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config)
        self.reputation = reputation or LeakyBucketReputation()
        self.telemetry = TransportTelemetry()
        self._handlers: Dict[str, Callable[[Any], Any]] = {}

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        self._handlers[topic] = handler

    async def send_payload(self, peer_id: str, payload: Union[bytes, str, dict, int]) -> bool:
        if isinstance(payload, bytes):
            data = payload
        elif isinstance(payload, str):
            data = payload.encode('utf-8')
        else:
            import json
            data = json.dumps(payload).encode('utf-8')
        
        self.telemetry.record_sent(len(data))
        return True

    async def receive_payload(self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str = 'default') -> Optional[Any]:
        if self.reputation.is_quarantined(peer_id):
            self.telemetry.record_dropped()
            logging.warning(f"Dropped payload from quarantined peer {peer_id}")
            return None

        if not self.rate_limiter.allow(peer_id):
            self.telemetry.record_dropped()
            return None

        if isinstance(payload, bytes):
            size = len(payload)
        elif isinstance(payload, str):
            size = len(payload.encode('utf-8'))
        else:
            import json
            size = len(json.dumps(payload).encode('utf-8'))

        self.telemetry.record_received(size)

        handler = self._handlers.get(topic) or self._handlers.get('default')
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(payload)
                else:
                    return handler(payload)
            except Exception as e:
                logging.error(f"Error in transport handler for topic {topic}: {e}")
                return None
        return payload

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "transport": self.telemetry.to_dict(),
            "rate_limiter": self.rate_limiter.get_metrics(),
            "reputation": self.reputation.get_metrics(),
        }


class TransportSocketReader:
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 0x474D4553) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[tuple]:
        header_data = await self.reader.read(28)
        if not header_data or len(header_data) < 28:
            return None
        
        from gossipmesh.p2p.parser import ZeroCopyPacketParser
        try:
            magic, msg_type, msg_id, payload_len = ZeroCopyPacketParser.parse_header(memoryview(header_data))
            if magic != self.expected_magic:
                return None
            payload_data = await self.reader.read(payload_len)
            return (msg_type, msg_id, memoryview(payload_data))
        except Exception:
            return None


class P2PSessionTransport:
    def __init__(self, max_messages: int = 1000, max_time_seconds: float = 300.0) -> None:
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self.message_count = 0
        self.start_time = time.monotonic()

    def is_expired(self) -> bool:
        if self.message_count >= self.max_messages:
            return True
        if (time.monotonic() - self.start_time) >= self.max_time_seconds:
            return True
        return False

    def record_message(self) -> None:
        self.message_count += 1
