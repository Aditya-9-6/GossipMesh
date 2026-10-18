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
    def __init__(self, max_messages: int=1000, max_time_seconds: float=300.0):
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
            return encrypt_payload(plaintext, self.rotator.current_key)

    def receive_message(self, ciphertext: bytes) -> bytes:
        with self._lock:
            self.message_count += 1
            if self._should_rotation_unlocked():
                self._trigger_rotation_unlocked()
            return decrypt_payload(ciphertext, self.rotator.current_key)


class TransportSocketReader:
    """Reads structured zero-copy packets from an asyncio StreamReader."""
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 0x474D4553) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        # Header is 4 (magic) + 2 (type) + 36 (msg_id) + 4 (length) = 46 bytes
        header_data = await self.reader.readexactly(46)
        if not header_data or len(header_data) < 46:
            raise ValueError("Incomplete packet header received")
        
        view = memoryview(header_data)
        magic, msg_type, msg_id, payload_len, payload_view = ZeroCopyPacketParser.parse_header(view)
        
        if magic != self.expected_magic:
            raise ValueError(f"Invalid packet magic: expected {self.expected_magic:#x}, got {magic:#x}")

        payload_bytes = await self.reader.readexactly(payload_len)
        return msg_type, msg_id, memoryview(payload_bytes)


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
                "bytes_received": self.bytes_received
            }


class GossipTransport:
    """High-performance Gossip Transport Layer combining rate limiting, encryption, erasure coding and telemetry."""
    def __init__(self, node_id: str, k: int = 4, m: int = 2, config: Optional[RateLimitConfig] = None):
        self.node_id = node_id
        self.k = k
        self.m = m
        self.rate_limiter = PeerRateLimiter(config=config or RateLimitConfig())
        self.telemetry = TransportTelemetry()
        self.erasure_coder = ErasureCoder(k=k, m=m)
        self.session = P2PSessionTransport()
        self.handlers: Dict[str, List[Callable[[Any], None]]] = {}
        self._lock = threading.Lock()

    def register_handler(self, topic: str, handler: Callable[[Any], None]) -> None:
        with self._lock:
            if topic not in self.handlers:
                self.handlers[topic] = []
            self.handlers[topic].append(handler)

    async def send_payload(self, peer_id: str, payload: Union[bytes, Dict[str, Any]], topic: str = "swarm", use_erasure: bool = False) -> bool:
        if not self.rate_limiter.acquire(peer_id):
            self.telemetry.record_dropped()
            return False

        if isinstance(payload, dict):
            data = json.dumps(payload).encode("utf-8")
        elif isinstance(payload, bytes):
            data = payload
        else:
            data = str(payload).encode("utf-8")

        if use_erasure:
            fragments = self.erasure_coder.encode(data)
            total_size = sum(len(f_bytes) for _, f_bytes in fragments)
            self.telemetry.record_sent(total_size)
            return True

        ciphertext = self.session.send_message(data)
        self.telemetry.record_sent(len(ciphertext))
        return True

    async def receive_payload(self, peer_id: str, payload: Union[bytes, Dict[str, Any]], topic: str = "swarm") -> Optional[Union[bytes, Dict[str, Any]]]:
        if not self.rate_limiter.acquire(peer_id):
            self.telemetry.record_dropped()
            return None

        if isinstance(payload, bytes):
            try:
                parsed_payload = json.loads(payload.decode("utf-8"))
            except Exception:
                parsed_payload = payload
            size = len(payload)
        else:
            parsed_payload = payload
            size = len(json.dumps(payload))

        self.telemetry.record_received(size)

        with self._lock:
            topic_handlers = self.handlers.get(topic, [])
            for h in topic_handlers:
                try:
                    h(parsed_payload)
                except Exception as exc:
                    logger.error(f"Error in handler for topic {topic}: {exc}")

        return parsed_payload

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        return self.telemetry.to_dict()