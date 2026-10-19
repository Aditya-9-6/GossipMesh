import asyncio
import json
import logging
import time
<<<<<<< HEAD
from typing import Optional, Callable, Awaitable, Any, Dict
=======
import threading
from typing import Any, Callable, Dict, Optional, Tuple, Union

>>>>>>> origin/main
from gossipmesh.p2p.parser import ZeroCopyPacketParser
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig
from gossipmesh.p2p.crypto import EphemeralSessionKeyRotator, encrypt_payload, decrypt_payload

logger = logging.getLogger(__name__)

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
<<<<<<< HEAD
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
=======
        with self._lock:
            if self._should_rotation_unlocked():
                self._trigger_rotation_unlocked()
            ciphertext = encrypt_payload(self.rotator.session_key, plaintext)
            self.rotator.message_counter += 1
            return ciphertext

    def receive_message(self, ciphertext: bytes) -> bytes:
        with self._lock:
            if self._should_rotation_unlocked():
                self._trigger_rotation_unlocked()
            plaintext = decrypt_payload(self.rotator.session_key, ciphertext)
            self.rotator.message_counter += 1
            return plaintext


class TransportTelemetry:
    """Telemetry tracking metrics for gossip transport layer."""

    def __init__(self) -> None:
        self.sent_messages: int = 0
        self.received_messages: int = 0
        self.sent_bytes: int = 0
        self.received_bytes: int = 0
        self.dropped_messages: int = 0

    def record_sent(self, size_bytes: int) -> None:
        self.sent_messages += 1
        self.sent_bytes += size_bytes

    def record_received(self, size_bytes: int) -> None:
        self.received_messages += 1
        self.received_bytes += size_bytes

    def record_dropped(self) -> None:
        self.dropped_messages += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sent_messages": self.sent_messages,
            "received_messages": self.received_messages,
            "sent_bytes": self.sent_bytes,
            "received_bytes": self.received_bytes,
            "dropped_messages": self.dropped_messages,
        }


class GossipTransport:
    """High-level P2P gossip transport integrating rate limiting, framing, and topic dispatch."""

    def __init__(
        self,
        node_id: str,
        config: Optional[RateLimitConfig] = None,
    ) -> None:
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config=config or RateLimitConfig())
        self.telemetry = TransportTelemetry()
        self.handlers: Dict[str, Callable[[Any], Any]] = {}

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        """Registers a callback handler for a gossip topic."""
        self.handlers[topic] = handler

    async def receive_payload(
        self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str = "default"
    ) -> Optional[Any]:
        """Receives, rate-limits, parses, and dispatches a payload from a peer."""
        if isinstance(payload, bytes):
            raw_bytes = payload
        elif isinstance(payload, str):
            raw_bytes = payload.encode("utf-8")
        elif isinstance(payload, dict):
            raw_bytes = json.dumps(payload).encode("utf-8")
        elif isinstance(payload, (int, float)):
            raw_bytes = str(payload).encode("utf-8")
        else:
            raw_bytes = str(payload).encode("utf-8")

        size_bytes = len(raw_bytes)
        allowed, _reason = await self.rate_limiter.check_and_consume(peer_id, size_bytes)
>>>>>>> origin/main
        if not allowed:
            self.telemetry.record_dropped()
            return None

<<<<<<< HEAD
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
=======
        self.telemetry.record_received(size_bytes)

        parsed_data: Any
        if isinstance(payload, dict):
            parsed_data = payload
        elif isinstance(payload, bytes):
            try:
                parsed_data = json.loads(payload.decode("utf-8", errors="ignore"))
            except Exception:
                parsed_data = {"raw": payload.decode("utf-8", errors="ignore")}
        elif isinstance(payload, str):
            try:
                parsed_data = json.loads(payload)
            except Exception:
                parsed_data = {"raw": payload}
        elif isinstance(payload, int):
            parsed_data = {"data": payload}
        else:
            parsed_data = {"raw": str(payload)}

        if topic in self.handlers:
            try:
                res = self.handlers[topic](parsed_data)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.error(f"Error in transport handler for topic {topic}: {e}")

        return parsed_data

    async def send_payload(self, peer_id: str, payload: Union[bytes, str, dict]) -> bool:
        """Simulates sending a payload to a peer with telemetry recording."""
        if isinstance(payload, bytes):
            raw_bytes = payload
        elif isinstance(payload, str):
            raw_bytes = payload.encode("utf-8")
        elif isinstance(payload, dict):
            raw_bytes = json.dumps(payload).encode("utf-8")
        else:
            raw_bytes = str(payload).encode("utf-8")

        self.telemetry.record_sent(len(raw_bytes))
>>>>>>> origin/main
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry metrics for transport and rate limiter."""
        limiter_metrics = await self.rate_limiter.get_metrics()
        return {
<<<<<<< HEAD
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
=======
            "transport": self.telemetry.to_dict(),
            "rate_limiter": limiter_metrics,
        }


class TransportSocketReader:
    """Low-level transport socket reader with zero-allocation memoryview parsing pipelines."""

    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 0x474D4553) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        """Reads a full gossip packet from the stream and returns header metadata and memoryview payload."""
        try:
            header_data = await self.reader.readexactly(ZeroCopyPacketParser.HEADER_SIZE)
        except asyncio.IncompleteReadError:
            return None
        
        if not header_data:
            return None
        
        header_view = memoryview(header_data)
        magic, msg_type, msg_id, payload_len, _ = ZeroCopyPacketParser.parse_header(header_view)
        
        if magic != self.expected_magic:
            logger.warning(f"Invalid packet magic received: {hex(magic)}")
            raise ValueError(f"Invalid packet magic: {hex(magic)}")

        try:
            payload_data = await self.reader.readexactly(payload_len)
        except asyncio.IncompleteReadError as e:
            raise ValueError(f"Incomplete payload read: expected {payload_len} bytes, got {len(e.partial)}")

        full_packet = header_data + payload_data
        full_view = memoryview(full_packet)
        _, _, _, _, payload_view = ZeroCopyPacketParser.parse_header(full_view)

        return msg_type, msg_id, payload_view
>>>>>>> origin/main
