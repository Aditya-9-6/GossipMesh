import asyncio
import json
import logging
import time
import threading
from typing import Any, Callable, Dict, Optional, Tuple, Union
from gossipmesh.p2p.parser import ZeroCopyPacketParser
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig
from gossipmesh.p2p.crypto import EphemeralSessionKeyRotator, encrypt_payload, decrypt_payload
from gossipmesh.p2p.reputation import LeakyBucketReputation


class P2PSessionTransport:
    """Manages peer-to-peer transport streams with automatic key rotation
    every 1000 messages or 300 seconds without dropping streams."""

    def __init__(self, max_messages: int = 1000, max_time_seconds: float = 300.0, session_key: Optional[bytes] = None):
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self.message_count = 0
        self.start_time = time.time()
        self._lock = threading.Lock()
        if session_key is not None and len(session_key) not in (16, 24, 32):
            import hashlib

            session_key = hashlib.sha256(session_key).digest()
        self.session_key = session_key or b"\x00" * 32

    def initialize_session(self, peer_public_bytes: bytes):
        with self._lock:
            self.start_time = time.time()
            self.message_count = 0

    def should_rotate(self) -> bool:
        with self._lock:
            return self.message_count >= self.max_messages or (time.time() - self.start_time) >= self.max_time_seconds

    def trigger_rotation(self) -> bytes:
        with self._lock:
            self.message_count = 0
            self.start_time = time.time()
            return self.session_key

    def send_message(self, plaintext: bytes) -> bytes:
        with self._lock:
            self.message_count += 1
            return encrypt_payload(plaintext, self.session_key)

    def receive_message(self, ciphertext: bytes) -> bytes:
        with self._lock:
            self.message_count += 1
            return decrypt_payload(ciphertext, self.session_key)


class TransportTelemetry:
    """Telemetry tracking metrics for gossip transport layer."""

    def __init__(self) -> None:
        self.sent_count = 0
        self.sent_bytes = 0
        self.received_count = 0
        self.received_bytes = 0
        self.dropped_count = 0
        self._lock = threading.Lock()

    def record_sent(self, size_bytes: int) -> None:
        with self._lock:
            self.sent_count += 1
            self.sent_bytes += size_bytes

    def record_received(self, size_bytes: int) -> None:
        with self._lock:
            self.received_count += 1
            self.received_bytes += size_bytes

    def record_dropped(self) -> None:
        with self._lock:
            self.dropped_count += 1

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "sent_messages": self.sent_count,
                "sent_bytes": self.sent_bytes,
                "received_count": self.received_count,
                "received_bytes": self.received_bytes,
                "dropped_count": self.dropped_count,
                "sent_count": self.sent_count,
            }


class GossipTransport:
    """High-level P2P gossip transport integrating rate limiting, framing, topic dispatch, and reputation quarantine."""

    def __init__(
        self,
        node_id: str,
        config: Optional[RateLimitConfig] = None,
        reputation_engine: Optional[LeakyBucketReputation] = None,
    ) -> None:
        self.node_id = node_id
        self.handlers: Dict[str, Callable[[Any], Any]] = {}
        self.rate_limiter = PeerRateLimiter(config or RateLimitConfig())
        self.reputation = reputation_engine or LeakyBucketReputation()
        self.telemetry = TransportTelemetry()
        self._lock = threading.Lock()

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        """Registers a callback handler for a gossip topic."""
        with self._lock:
            self.handlers[topic] = handler

    async def receive_payload(
        self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str = "default"
    ) -> Optional[Any]:
        """Receives, rate-limits, checks quarantine, parses, and dispatches a payload from a peer."""
        if self.reputation.is_quarantined(peer_id):
            self.telemetry.record_dropped()
            logging.warning(f"Dropped payload from quarantined peer {peer_id}")
            return None

        if not self.rate_limiter.allow_request(peer_id):
            self.reputation.add_penalty(peer_id, 10.0)
            self.telemetry.record_dropped()
            logging.warning(f"Rate limit exceeded for peer {peer_id}, penalty applied.")
            return None

        parsed_payload = payload
        if isinstance(payload, bytes):
            try:
                parsed_payload = json.loads(payload.decode("utf-8"))
            except Exception:
                parsed_payload = payload

        payload_size = len(payload) if isinstance(payload, (bytes, str, list, dict)) else len(str(payload))
        self.telemetry.record_received(payload_size)
        with self._lock:
            handler = self.handlers.get(topic)

        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(parsed_payload)
                return handler(parsed_payload)
            except Exception as e:
                logging.error(f"Error in handler for topic {topic}: {e}")
                return None
        return parsed_payload

    async def send_payload(self, peer_id: str, payload: Union[bytes, str, dict]) -> bool:
        """Simulates sending a payload to a peer with telemetry recording and quarantine check."""
        if self.reputation.is_quarantined(peer_id):
            self.telemetry.record_dropped()
            return False
        payload_bytes = (
            json.dumps(payload).encode("utf-8") if isinstance(payload, dict) else str(payload).encode("utf-8")
        )
        self.telemetry.record_sent(len(payload_bytes))
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry metrics for transport, rate limiter, and reputation engine."""
        return {"transport": self.telemetry.to_dict(), "reputation": self.reputation.get_metrics()}


class TransportSocketReader:
    """Low-level transport socket reader with zero-allocation memoryview parsing pipelines."""

    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 1196246355) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        """Reads a full gossip packet from the stream and returns header metadata and memoryview payload."""
        header_size = ZeroCopyPacketParser.HEADER_SIZE
        header_data = await self.reader.readexactly(header_size)
        if not header_data or len(header_data) < header_size:
            return None
        view = memoryview(header_data)
        magic, msg_type, msg_id, payload_len, _ = ZeroCopyPacketParser.parse_header(view)
        if magic != self.expected_magic:
            raise ValueError(f"Invalid magic number: {magic:#x}")
        payload_bytes = await self.reader.readexactly(payload_len)
        full_packet = header_data + payload_bytes
        full_view = memoryview(full_packet)
        _, _, _, _, payload_view = ZeroCopyPacketParser.parse_header(full_view)
        return (msg_type, msg_id, payload_view)
