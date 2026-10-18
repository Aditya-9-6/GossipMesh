import asyncio
import json
import logging
import time
from typing import Optional, Callable, Awaitable, Any, Dict
from gossipmesh.p2p.parser import ZeroCopyPacketParser
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)


class P2PSessionTransport:
    """Manages P2P transport sessions, session keys, and message counters for rotation."""

    def __init__(self, max_messages: int = 1000, max_time_seconds: float = 3600.0) -> None:
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self.message_count = 0
        self.start_time = time.time()
        self.peer_public_key: Optional[bytes] = None

    def initialize_session(self, peer_public_bytes: bytes) -> None:
        self.peer_public_key = peer_public_bytes
        self.start_time = time.time()
        self.message_count = 0

    def send_message(self, plaintext: bytes) -> bytes:
        self.message_count += 1
        return plaintext

    def should_rotate(self) -> bool:
        elapsed = time.time() - self.start_time
        return (self.message_count >= self.max_messages) or (elapsed >= self.max_time_seconds)


class TransportTelemetry:
    def __init__(self) -> None:
        self.sent_messages = 0
        self.received_messages = 0
        self.dropped_messages = 0
        self.sent_bytes = 0
        self.received_bytes = 0


class GossipTransport:
    """Main P2P Gossip Transport layer managing message handlers, rate limiting, and metrics."""

    def __init__(self, node_id: str, config: Optional[RateLimitConfig] = None) -> None:
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config=config)
        self.handlers: Dict[str, Callable[[Any], Any]] = {}
        self.telemetry = TransportTelemetry()

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Any, topic: str = "default") -> Optional[Any]:
        payload_bytes = b""
        if isinstance(payload, bytes):
            payload_bytes = payload
            try:
                parsed = json.loads(payload.decode('utf-8'))
            except Exception:
                parsed = {"raw": payload.decode('utf-8', errors='ignore')}
        elif isinstance(payload, str):
            payload_bytes = payload.encode('utf-8')
            try:
                parsed = json.loads(payload)
            except Exception:
                parsed = {"raw": payload}
        elif isinstance(payload, dict):
            payload_bytes = json.dumps(payload).encode('utf-8')
            parsed = payload
        else:
            payload_bytes = str(payload).encode('utf-8')
            parsed = {"data": payload}

        allowed, reason = await self.rate_limiter.check_and_consume(peer_id, len(payload_bytes))
        if not allowed:
            self.telemetry.dropped_messages += 1
            return None

        self.telemetry.received_messages += 1
        self.telemetry.received_bytes += len(payload_bytes)

        if topic in self.handlers:
            try:
                handler = self.handlers[topic]
                if asyncio.iscoroutinefunction(handler):
                    await handler(parsed)
                else:
                    handler(parsed)
            except Exception as e:
                logger.error(f"Error in transport handler for topic {topic}: {e}")

        return parsed

    async def send_payload(self, peer_id: str, payload: Any) -> bool:
        if isinstance(payload, dict):
            b = json.dumps(payload).encode('utf-8')
        elif isinstance(payload, str):
            b = payload.encode('utf-8')
        elif isinstance(payload, bytes):
            b = payload
        else:
            b = str(payload).encode('utf-8')

        self.telemetry.sent_messages += 1
        self.telemetry.sent_bytes += len(b)
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        limiter_metrics = await self.rate_limiter.get_metrics()
        return {
            "transport": {
                "sent_messages": self.telemetry.sent_messages,
                "received_messages": self.telemetry.received_messages,
                "dropped_messages": self.telemetry.dropped_messages,
                "sent_bytes": self.telemetry.sent_bytes,
                "received_bytes": self.telemetry.received_bytes,
            },
            "rate_limiter": limiter_metrics
        }


class TransportReader:
    """Low-level socket transport reader utilizing zero-copy buffer parsing."""
    
    def __init__(self, reader: asyncio.StreamReader, on_message: Callable[[memoryview], Awaitable[None]]) -> None:
        self.reader = reader
        self.on_message = on_message
        self._buffer = bytearray()

    async def start_reading(self) -> None:
        """Reads incoming stream data and dispatches parsed packets with zero allocations."""
        try:
            while True:
                chunk = await self.reader.read(4096)
                if not chunk:
                    break
                self._buffer.extend(chunk)
                await self._process_buffer()
        except Exception as e:
            logger.error(f"Transport reader error: {e}")
            raise

    async def _process_buffer(self) -> None:
        """Processes internal bytearray buffer via memoryviews."""
        mv = memoryview(self._buffer)
        offset = 0
        
        try:
            while len(mv) - offset >= ZeroCopyPacketParser.HEADER_SIZE:
                sub_mv = mv[offset:]
                magic, length = ZeroCopyPacketParser.parse_header(sub_mv)
                total_packet_size = ZeroCopyPacketParser.HEADER_SIZE + length
                
                if len(sub_mv) < total_packet_size:
                    break  
                
                payload_mv = sub_mv[ZeroCopyPacketParser.HEADER_SIZE:total_packet_size]
                await self.on_message(payload_mv)
                offset += total_packet_size
        finally:
            if offset > 0:
                del self._buffer[:offset]
