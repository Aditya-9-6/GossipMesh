import asyncio
import json
import logging
import time
import threading
from typing import Any, Callable, Dict, Optional, Tuple, Union
from gossipmesh.p2p.parser import ZeroCopyPacketParser
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig
from gossipmesh.p2p.crypto import EphemeralSessionKeyRotator, encrypt_payload, decrypt_payload
from gossipmesh.p2p.fountain import FountainEncoder, FountainDecoder

class P2PSessionTransport:
    """Manages peer-to-peer transport streams with automatic key rotation
every 1000 messages or 300 seconds without dropping streams."""
    def __init__(self, max_messages: int=1000, max_time_seconds: float=300.0) -> None:
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self.message_count = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        self.rotator = EphemeralSessionKeyRotator()

    def initialize_session(self, peer_public_bytes: bytes) -> None:
        with self.lock:
            self.rotator.initialize(peer_public_bytes)

    def _should_rotation_unlocked(self) -> bool:
        if self.message_count >= self.max_messages:
            return True
        if time.time() - self.start_time >= self.max_time_seconds:
            return True
        return False

    def should_rotate(self) -> bool:
        with self.lock:
            return self._should_rotation_unlocked()

    def _trigger_rotation_unlocked(self) -> bytes:
        self.message_count = 0
        self.start_time = time.time()
        return self.rotator.rotate()

    def trigger_rotation(self) -> bytes:
        with self.lock:
            return self._trigger_rotation_unlocked()

    def send_message(self, plaintext: bytes) -> bytes:
        with self.lock:
            self.message_count += 1
            if self._should_rotation_unlocked():
                self._trigger_rotation_unlocked()
            return encrypt_payload(plaintext, self.rotator.current_key)

    def receive_message(self, ciphertext: bytes) -> bytes:
        with self.lock:
            self.message_count += 1
            return decrypt_payload(ciphertext, self.rotator.current_key)

class TransportTelemetry:
    """Telemetry tracking metrics for gossip transport layer."""
    def __init__(self) -> None:
        self.sent_count = 0
        self.received_count = 0
        self.dropped_count = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self.lock = threading.Lock()

    def record_sent(self, size_bytes: int) -> None:
        with self.lock:
            self.sent_count += 1
            self.bytes_sent += size_bytes

    def record_received(self, size_bytes: int) -> None:
        with self.lock:
            self.received_count += 1
            self.bytes_received += size_bytes

    def record_dropped(self) -> None:
        with self.lock:
            self.dropped_count += 1

    def to_dict(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "sent_count": self.sent_count,
                "received_count": self.received_count,
                "dropped_count": self.dropped_count,
                "bytes_sent": self.bytes_sent,
                "bytes_received": self.bytes_received,
            }

class GossipTransport:
    """High-level P2P gossip transport integrating rate limiting, framing, and topic dispatch."""
    def __init__(self, node_id: str, config: Optional[RateLimitConfig]=None) -> None:
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config or RateLimitConfig())
        self.handlers: Dict[str, Callable[[Any], Any]] = {}
        self.telemetry = TransportTelemetry()

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        """Registers a callback handler for a gossip topic."""
        self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str='default') -> Optional[Any]:
        """Receives, rate-limits, parses, and dispatches a payload from a peer."""
        if not self.rate_limiter.check_rate_limit(peer_id):
            self.telemetry.record_dropped()
            return None
        
        payload_bytes = json.dumps(payload).encode('utf-8') if isinstance(payload, (dict, list, int, float))
        self.telemetry.record_received(len(payload_bytes) if isinstance(payload_bytes, bytes) else 0)
        
        handler = self.handlers.get(topic)
        if handler:
            return handler(payload)
        return payload

    async def send_payload(self, peer_id: str, payload: Union[bytes, str, dict]) -> bool:
        """Simulates sending a payload to a peer with telemetry recording."""
        data = json.dumps(payload).encode('utf-8') if isinstance(payload, (dict, list)) else payload
        if isinstance(data, str):
            data = data.encode('utf-8')
        self.telemetry.record_sent(len(data))
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry metrics for transport and rate limiter."""
        return self.telemetry.to_dict()

class TransportSocketReader:
    """Low-level transport socket reader with zero-allocation memoryview parsing pipelines."""
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int=1196246355) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        """Reads a full gossip packet from the stream and returns header metadata and memoryview payload."""
        header_data = await self.reader.readexactly(12)
        if len(header_data) < 12:
            return None
        magic, version, length = struct.unpack("!III", header_data)
        if magic != self.expected_magic:
            return None
        payload = await self.reader.readexactly(length)
        return (version, "default", memoryview(payload))
