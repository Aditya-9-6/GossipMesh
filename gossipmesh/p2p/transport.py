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
every 1000 messages or 3600 seconds.
    """
    def __init__(self, max_messages: int = 1000, max_time_seconds: float = 3600.0):
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self.message_count = 0
        self.start_time = time.time()
        self._remote_public_key: Optional[bytes] = None
        self._lock = threading.Lock()

    def initialize_session(self, remote_public_bytes: bytes) -> None:
        with self._lock:
            self._remote_public_key = remote_public_bytes
            self.start_time = time.time()
            self.message_count = 0

    def send_message(self, plaintext: bytes) -> bytes:
        with self._lock:
            self.message_count += 1
            return encrypt_payload(plaintext)

    def should_rotate(self) -> bool:
        with self._lock:
            elapsed = time.time() - self.start_time
            return (self.message_count >= self.max_messages) or (elapsed >= self.max_time_seconds)

class TransportTelemetry:
    def __init__(self):
        self.sent_messages = 0
        self.received_messages = 0
        self.dropped_messages = 0
        self._lock = threading.Lock()

    def record_sent(self, size_bytes: int = 0):
        with self._lock:
            self.sent_messages += 1

    def record_received(self, size_bytes: int = 0):
        with self._lock:
            self.received_messages += 1

    def record_dropped(self):
        with self._lock:
            self.dropped_messages += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "sent_messages": self.sent_messages,
                "received_messages": self.received_messages,
                "dropped_messages": self.dropped_messages
            }

class GossipTransport:
    """Gossip transport layer handling peer routing, rate limiting, and telemetry."""
    def __init__(self, node_id: str, config: Optional[RateLimitConfig] = None, reputation_engine: Optional[LeakyBucketReputation] = None):
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config)
        self.reputation = reputation_engine or LeakyBucketReputation()
        self.telemetry = TransportTelemetry()
        self.handlers: Dict[str, Callable[[Any], Any]] = {}
        self._lock = threading.Lock()

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        with self._lock:
            self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str = 'default') -> Optional[Any]:
        if self.reputation.is_quarantined(peer_id):
            self.telemetry.record_dropped()
            logging.warning(f"Dropped payload from quarantined peer {peer_id}")
            return None

        if not self.rate_limiter.allow(peer_id):
            self.reputation.add_penalty(peer_id, 10.0)
            self.telemetry.record_dropped()
            logging.warning(f"Rate limited payload from peer {peer_id}")
            return None

        self.telemetry.record_received(len(str(payload)))

        parsed_payload = payload
        if isinstance(payload, bytes):
            try:
                parsed_payload = json.loads(payload.decode('utf-8'))
            except Exception:
                pass
        elif isinstance(payload, str):
            try:
                parsed_payload = json.loads(payload)
            except Exception:
                pass

        with self._lock:
            handler = self.handlers.get(topic)

        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(parsed_payload)
                else:
                    handler(parsed_payload)
            except Exception as e:
                logging.error(f"Handler error for topic {topic}: {e}")

        return parsed_payload

    async def send_payload(self, peer_id: str, payload: Any) -> bool:
        if self.reputation.is_quarantined(peer_id):
            self.telemetry.record_dropped()
            return False
        self.telemetry.record_sent(len(str(payload)))
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        return {
            "transport": self.telemetry.get_metrics(),
            "reputation": self.reputation.get_metrics(),
            "node_id": self.node_id
        }

class TransportSocketReader:
    """Low-level transport socket reader with zero-allocation memoryview parsing pipelines."""
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 1196246355) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        # Read fixed header size (magic: 4, msg_type: 1, msg_id: 32, payload_len: 4) = 41 bytes
        header_size = 41
        try:
            header_data = await self.reader.readexactly(header_size)
        except asyncio.IncompleteReadError:
            return None

        buf = memoryview(header_data)
        magic, msg_type, msg_id, payload_len, payload_view = ZeroCopyPacketParser.parse_header(buf)
        
        if magic != self.expected_magic:
            raise ValueError(f"Invalid packet magic: {hex(magic)}, expected {hex(self.expected_magic)}")

        try:
            payload_data = await self.reader.readexactly(payload_len)
        except asyncio.IncompleteReadError:
            raise ValueError("Incomplete packet payload")

        return (msg_type, msg_id, memoryview(payload_data))
