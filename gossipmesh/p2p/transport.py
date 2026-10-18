import asyncio
import json
import logging
import uuid
import time
from typing import Any, Callable, Dict, Optional, Union

from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig
from gossipmesh.p2p.reputation import LeakyBucketReputation
from gossipmesh.p2p.parser import ZeroCopyPacketParser

logger = logging.getLogger(__name__)


class TransportTelemetry:
    def __init__(self) -> None:
        self.sent_messages = 0
        self.received_messages = 0
        self.dropped_messages = 0

    def record_sent(self) -> None:
        self.sent_messages += 1

    def record_received(self) -> None:
        self.received_messages += 1

    def record_dropped(self) -> None:
        self.dropped_messages += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sent_messages": self.sent_messages,
            "received_messages": self.received_messages,
            "dropped_messages": self.dropped_messages,
        }


class TransportSocketReader:
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 0x474D4553) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[tuple[int, str, memoryview]]:
        try:
            header_bytes = await self.reader.readexactly(ZeroCopyPacketParser.HEADER_SIZE)
        except asyncio.IncompleteReadError:
            return None

        magic, msg_type, msg_id, payload_len = ZeroCopyPacketParser.deserialize_header(header_bytes)
        if magic != self.expected_magic:
            raise ValueError(f"Invalid packet magic: {hex(magic)}, expected {hex(self.expected_magic)}")

        try:
            payload_bytes = await self.reader.readexactly(payload_len)
        except asyncio.IncompleteReadError:
            return None

        return msg_type, msg_id, memoryview(payload_bytes)


class GossipTransport:
    def __init__(self, node_id: str, config: Optional[RateLimitConfig] = None) -> None:
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config)
        self.reputation = LeakyBucketReputation()
        self.telemetry = TransportTelemetry()
        self.handlers: Dict[str, Callable[[Any], Any]] = {}

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str = 'default') -> Optional[Any]:
        if self.reputation.is_quarantined(peer_id):
            self.telemetry.record_dropped()
            logging.warning(f"Dropped payload from quarantined peer {peer_id}")
            return None

        if not self.rate_limiter.allow(peer_id):
            self.telemetry.record_dropped()
            return None

        self.telemetry.record_received()
        
        parsed_payload = payload
        if isinstance(payload, bytes):
            try:
                parsed_payload = json.loads(payload.decode('utf-8'))
            except Exception:
                pass

        handler = self.handlers.get(topic)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(parsed_payload)
                else:
                    handler(parsed_payload)
            except Exception as e:
                logger.error(f"Error in handler for topic {topic}: {e}")

        return parsed_payload

    async def send_payload(self, peer_id: str, payload: Any) -> bool:
        self.telemetry.record_sent()
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "transport": self.telemetry.to_dict()
        }


class P2PSessionTransport:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader = reader
        self.writer = writer
