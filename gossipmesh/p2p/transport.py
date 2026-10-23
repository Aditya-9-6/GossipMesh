import asyncio
import json
import logging
import time
import threading
from typing import Any, Callable, Dict, Optional, Tuple, Union

from gossipmesh.p2p.parser import ZeroCopyPacketParser
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig
from gossipmesh.p2p.crypto import EphemeralSessionKeyRotator, encrypt_payload, decrypt_payload

logger = logging.getLogger(__name__)


class P2PSessionTransport:
    """Manages peer-to-peer transport streams with automatic key rotation
    every 1000 messages or 300 seconds without dropping streams."""

    def __init__(self, max_messages: int = 1000, max_time_seconds: float = 300.0):
        self.rotator = EphemeralSessionKeyRotator()
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self._lock = threading.Lock()
        self.creation_time = time.time()

    def initialize_session(self, peer_public_bytes: bytes):
        with self._lock:
            self.rotator.derive_session_key(peer_public_bytes)
            self.creation_time = time.time()

    def _should_rotation_unlocked(self) -> bool:
        if self.rotator.message_counter >= self.max_messages:
            return True
        if (time.time() - self.creation_time) >= self.max_time_seconds:
            return True
        return False

    def should_rotate(self) -> bool:
        with self._lock:
            return self._should_rotation_unlocked()

    def _trigger_rotation_unlocked(self) -> bytes:
        _, new_pub_bytes = self.rotator.rotate()
        self.creation_time = time.time()
        return new_pub_bytes

    def trigger_rotation(self) -> bytes:
        with self._lock:
            return self._trigger_rotation_unlocked()

    def send_message(self, plaintext: bytes) -> bytes:
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
        if not allowed:
            self.telemetry.record_dropped()
            return None

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
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry metrics for transport and rate limiter."""
        limiter_metrics = await self.rate_limiter.get_metrics()
        return {
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
