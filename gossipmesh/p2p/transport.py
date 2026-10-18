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
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self.message_count = 0
        self.start_time = time.time()
        self._lock = threading.Lock()
        self.rotator = EphemeralSessionKeyRotator()

    def initialize_session(self, peer_public_bytes: bytes):
        with self._lock:
            self.rotator.initialize_peer(peer_public_bytes)

    def _should_rotation_unlocked(self) -> bool:
        elapsed = time.time() - self.start_time
        return self.message_count >= self.max_messages or elapsed >= self.max_time_seconds

    def should_rotate(self) -> bool:
        with self._lock:
            return self._should_rotation_unlocked()

    def _trigger_rotation_unlocked(self) -> bytes:
        self.message_count = 0
        self.start_time = time.time()
        return self.rotator.rotate()

    def trigger_rotation(self) -> bytes:
        with self._lock:
            return self._trigger_rotation_unlocked()

    def send_message(self, plaintext: bytes) -> bytes:
        with self._lock:
            self.message_count += 1
            if self._should_rotation_unlocked():
                self._trigger_rotation_unlocked()
            session_key = self.rotator.get_active_key()
            return encrypt_payload(plaintext, session_key)

    def receive_message(self, ciphertext: bytes) -> bytes:
        with self._lock:
            session_key = self.rotator.get_active_key()
            return decrypt_payload(ciphertext, session_key)

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
                "sent_count": self.sent_count,
                "sent_bytes": self.sent_bytes,
                "received_count": self.received_count,
                "received_bytes": self.received_bytes,
                "dropped_count": self.dropped_count,
            }

class GossipTransport:
    """High-level P2P gossip transport integrating rate limiting, framing, and topic dispatch."""
    def __init__(self, node_id: str, config: Optional[RateLimitConfig] = None) -> None:
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config)
        self.telemetry = TransportTelemetry()
        self.handlers: Dict[str, Callable[[Any], Any]] = {}
        self.parser = ZeroCopyPacketParser()

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        """Registers a callback handler for a gossip topic."""
        self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str = 'default') -> Optional[Any]:
        """Receives, rate-limits, parses, and dispatches a payload from a peer."""
        if not self.rate_limiter.acquire(peer_id):
            self.telemetry.record_dropped()
            logger.warning(f"Rate limit exceeded for peer {peer_id}")
            return None

        data_bytes = json.dumps(payload).encode('utf-8') if not isinstance(payload, bytes) else payload
        self.telemetry.record_received(len(data_bytes))

        handler = self.handlers.get(topic)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                return await handler(payload)
            return handler(payload)
        return payload

    async def send_payload(self, peer_id: str, payload: Union[bytes, str, dict]) -> bool:
        """Simulates sending a payload to a peer with telemetry recording and outbound rate limiting."""
        if not self.rate_limiter.acquire(peer_id):
            self.telemetry.record_dropped()
            return False

        data_bytes = json.dumps(payload).encode('utf-8') if not isinstance(payload, bytes) else payload
        self.telemetry.record_sent(len(data_bytes))
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry metrics for transport and rate limiter."""
        metrics = self.telemetry.to_dict()
        metrics["rate_limiter"] = self.rate_limiter.get_metrics()
        return metrics

class TransportSocketReader:
    """Low-level transport socket reader with zero-allocation memoryview parsing pipelines."""
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 1196246355) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        """Reads a full gossip packet from the stream and returns header metadata and memoryview payload."""
        header_data = await self.reader.readexactly(12)
        if len(header_data) < 12:
            return None
        magic = int.from_bytes(header_data[0:4], byteorder='big')
        if magic != self.expected_magic:
            return None
        length = int.from_bytes(header_data[4:8], byteorder='big')
        topic_len = int.from_bytes(header_data[8:12], byteorder='big')
        
        topic_bytes = await self.reader.readexactly(topic_len)
        topic = topic_bytes.decode('utf-8')
        
        payload_data = await self.reader.readexactly(length)
        return (magic, topic, memoryview(payload_data))
