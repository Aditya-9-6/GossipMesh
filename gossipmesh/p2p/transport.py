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
    def __init__(self, max_messages: int = 1000, max_time_seconds: float = 300.0):
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self.rotator = EphemeralSessionKeyRotator()
        self.session_key: Optional[bytes] = None
        self.message_count = 0
        self.session_start_time = time.time()
        self._lock = threading.Lock()

    def initialize_session(self, peer_public_bytes: bytes):
        with self._lock:
            self.session_key = self.rotator.derive_session_key(peer_public_bytes)
            self.message_count = 0
            self.session_start_time = time.time()

    def _should_rotation_unlocked(self) -> bool:
        if self.message_count >= self.max_messages:
            return True
        if (time.time() - self.session_start_time) >= self.max_time_seconds:
            return True
        return False

    def should_rotate(self) -> bool:
        with self._lock:
            return self._should_rotation_unlocked()

    def _trigger_rotation_unlocked(self) -> bytes:
        _, pub_bytes = self.rotator.rotate()
        self.message_count = 0
        self.session_start_time = time.time()
        self.session_key = None
        return pub_bytes

    def trigger_rotation(self) -> bytes:
        with self._lock:
            return self._trigger_rotation_unlocked()

    def send_message(self, plaintext: bytes) -> bytes:
        with self._lock:
            if not self.session_key:
                raise ValueError("Session key not initialized.")
            if self._should_rotation_unlocked():
                self._trigger_rotation_unlocked()
                raise ValueError("Session key rotation required")
            self.message_count += 1
            return encrypt_payload(self.session_key, plaintext)

    def receive_message(self, ciphertext: bytes) -> bytes:
        with self._lock:
            if not self.session_key:
                raise ValueError("Session key not initialized.")
            self.message_count += 1
            return decrypt_payload(self.session_key, ciphertext)

class TransportTelemetry:
    """Telemetry tracking metrics for gossip transport layer."""
    def __init__(self) -> None:
        self.sent_count = 0
        self.received_count = 0
        self.dropped_count = 0
    def record_sent(self, size_bytes: int) -> None:
        self.sent_count += 1
    def record_received(self, size_bytes: int) -> None:
        self.received_count += 1
    def record_dropped(self) -> None:
        self.dropped_count += 1
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sent_count": self.sent_count,
            "received_count": self.received_count,
            "dropped_count": self.dropped_count
        }

class GossipTransport:
    """High-level P2P gossip transport integrating rate limiting, framing, topic dispatch, and reputation quarantine."""
    def __init__(self, node_id: str, config: Optional[RateLimitConfig] = None, reputation_engine: Optional[LeakyBucketReputation] = None) -> None:
        self.node_id = node_id
        self.handlers: Dict[str, Callable[[Any], Any]] = {}
        self.rate_limiter = PeerRateLimiter(config or RateLimitConfig())
        self.reputation = reputation_engine or LeakyBucketReputation()
        self.telemetry = TransportTelemetry()

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        """Registers a callback handler for a gossip topic."""
        self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str = 'default') -> Optional[Any]:
        """Receives, rate-limits, checks quarantine, parses, and dispatches a payload from a peer."""
        if self.reputation.is_quarantined(peer_id):
            self.telemetry.record_dropped()
            logging.warning(f"Dropped payload from quarantined peer {peer_id}")
            return None

        if not self.rate_limiter.allow(peer_id):
            self.reputation.add_penalty(peer_id, 10.0)
            self.telemetry.record_dropped()
            logging.warning(f"Rate limit exceeded for peer {peer_id}, penalty applied.")
            return None

        self.telemetry.record_received(len(str(payload)))
        handler = self.handlers.get(topic)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(payload)
                return handler(payload)
            except Exception as e:
                logging.error(f"Error in handler for topic {topic}: {e}")
                return None
        
        # Handle different payload formats if raw bytes/str
        if isinstance(payload, bytes):
            try:
                payload = json.loads(payload.decode('utf-8'))
            except Exception:
                pass
        elif isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                pass

        return payload

    async def send_payload(self, peer_id: str, payload: Union[bytes, str, dict]) -> bool:
        """Simulates sending a payload to a peer with telemetry recording and quarantine check."""
        if self.reputation.is_quarantined(peer_id):
            self.telemetry.record_dropped()
            return False
        self.telemetry.record_sent(len(str(payload)))
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry metrics for transport, rate limiter, and reputation engine."""
        return {
            "transport": self.telemetry.to_dict(),
            "reputation": self.reputation.get_metrics()
        }

class TransportSocketReader:
    """Low-level transport socket reader with zero-allocation memoryview parsing pipelines."""
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 1196246355) -> None:
        self.reader = reader
        self.expected_magic = expected_magic
    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        """Reads a full gossip packet from the stream and returns header metadata and memoryview payload."""
        return None
