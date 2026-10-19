import asyncio
import json
import logging
import time
import threading
from typing import Any, Callable, Dict, Optional, Tuple, Union
from gossipmesh.p2p.parser import ZeroCopyPacketParser
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig
from gossipmesh.p2p.crypto import EphemeralSessionKeyRotator, encrypt_payload, decrypt_payload
from gossipmesh.p2p.erasure import ErasureCoder

logger = logging.getLogger(__name__)


class P2PSessionTransport:
    """Manages peer-to-peer transport streams with automatic key rotation
    every 1000 messages or 300 seconds without dropping streams."""

    def __init__(self, max_messages: int = 1000, max_time_seconds: float = 300.0):
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self.message_count = 0
        self.created_at = time.time()
        self.rotator = EphemeralSessionKeyRotator()
        self._lock = threading.Lock()

    def initialize_session(self, peer_public_bytes: bytes):
        with self._lock:
            self.rotator.derive_session_key(peer_public_bytes)

    def _should_rotation_unlocked(self) -> bool:
        if self.message_count >= self.max_messages:
            return True
        if time.time() - self.created_at >= self.max_time_seconds:
            return True
        return False

    def should_rotate(self) -> bool:
        with self._lock:
            return self._should_rotation_unlocked()

    def _trigger_rotation_unlocked(self) -> bytes:
        self.message_count = 0
        self.created_at = time.time()
        return self.rotator.rotate_key()

    def trigger_rotation(self) -> bytes:
        with self._lock:
            return self._trigger_rotation_unlocked()

    def send_message(self, plaintext: bytes) -> bytes:
        with self._lock:
            self.message_count += 1
            if self._should_rotation_unlocked():
                self._trigger_rotation_unlocked()
            return encrypt_payload(self.rotator.get_current_key(), plaintext)

    def receive_message(self, ciphertext: bytes) -> bytes:
        with self._lock:
            self.message_count += 1
            if self._should_rotation_unlocked():
                self._trigger_rotation_unlocked()
            return decrypt_payload(ciphertext, self.rotator.get_current_key())


class TransportTelemetry:
    """Telemetry tracking metrics for gossip transport layer."""

    def __init__(self) -> None:
        self.sent_count = 0
        self.received_count = 0
        self.dropped_count = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self._lock = threading.Lock()

    def record_sent(self, size_bytes: int) -> None:
        with self._lock:
            self.sent_count += 1
            self.bytes_sent += size_bytes

    def record_received(self, size_bytes: int) -> None:
        with self._lock:
            self.received_count += 1
            self.bytes_received += size_bytes

    def record_dropped(self) -> None:
        with self._lock:
            self.dropped_count += 1

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "sent_count": self.sent_count,
                "received_count": self.received_count,
                "dropped_count": self.dropped_count,
                "bytes_sent": self.bytes_sent,
                "bytes_received": self.bytes_received,
            }


class TransportSocketReader:
    """Reads zero-copy packet structures from an asyncio stream reader."""

    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 0x474D4553) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        header_bytes = await self.reader.readexactly(45)
        buf = memoryview(header_bytes)
        magic, msg_type, msg_id, payload_len, payload_view = ZeroCopyPacketParser.parse_header(
            buf, expected_magic=self.expected_magic
        )
        payload_bytes = await self.reader.readexactly(payload_len)
        return magic, msg_id, memoryview(payload_bytes)


class GossipTransport:
    """Main GossipMesh transport layer integrating erasure coding, rate limiting, and handlers."""

    def __init__(self, node_id: str, k: int = 4, m: int = 2, config: Optional[RateLimitConfig] = None) -> None:
        self.node_id = node_id
        self.k = k
        self.m = m
        self.telemetry = TransportTelemetry()
        self.rate_limiter = PeerRateLimiter(config=config or RateLimitConfig())
        self.erasure_coder = ErasureCoder(k=k, m=m)
        self.handlers: Dict[str, Callable[[Any], None]] = {}
        self._lock = threading.Lock()

    def register_handler(self, topic: str, handler: Callable[[Any], None]) -> None:
        with self._lock:
            self.handlers[topic] = handler

    async def send_payload(
        self, peer_id: str, payload: Union[bytes, str, dict, int], use_erasure: bool = False
    ) -> bool:
        if isinstance(payload, dict):
            data = json.dumps(payload).encode("utf-8")
        elif isinstance(payload, str):
            data = payload.encode("utf-8")
        elif isinstance(payload, int):
            data = str(payload).encode("utf-8")
        elif isinstance(payload, bytes):
            data = payload
        else:
            data = bytes(payload)

        if use_erasure:
            fragments = self.erasure_coder.encode(data)
            total_size = sum(len(f[1]) for f in fragments)
            self.telemetry.record_sent(total_size)
        else:
            self.telemetry.record_sent(len(data))
        return True

    async def receive_payload(
        self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str = "default"
    ) -> Optional[Any]:
        if not self.rate_limiter.allow(peer_id):
            self.telemetry.record_dropped()
            return None

        if isinstance(payload, bytes):
            try:
                payload = json.loads(payload.decode("utf-8"))
            except Exception:
                pass

        if isinstance(payload, (bytes, str, dict, int)):
            size = len(json.dumps(payload)) if isinstance(payload, dict) else len(str(payload))
            self.telemetry.record_received(size)

        handler = self.handlers.get(topic)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(payload)
                else:
                    handler(payload)
            except Exception as e:
                logger.error(f"Error in handler for topic {topic}: {e}")
        return payload

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        metrics = self.telemetry.to_dict()
        metrics["rate_limiter_stats"] = self.rate_limiter.get_stats()
        return metrics
