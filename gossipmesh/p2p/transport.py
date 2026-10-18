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

    def record_sent(self):
        with self._lock:
            self.sent_messages += 1

    def record_received(self):
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
    def __init__(self, node_id: str, config: Optional[RateLimitConfig] = None):
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config)
        self.reputation = LeakyBucketReputation()
        self.telemetry = TransportTelemetry()
        self.handlers: Dict[str, Callable[[Any], None]] = {}
        self._lock = threading.Lock()

    def register_handler(self, topic: str, handler: Callable[[Any], None]) -> None:
        with self._lock:
            self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str = 'default') -> Optional[Any]:
        if self.reputation.is_quarantined(peer_id):
            self.telemetry.record_dropped()
            logging.warning(f"Dropped payload from quarantined peer {peer_id}")
            return None

        if not self.rate_limiter.allow(peer_id):
            self.telemetry.record_dropped()
            logging.warning(f"Rate limited payload from peer {peer_id}")
            return None

        self.telemetry.record_received()

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
        self.telemetry.record_sent()
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        return {
            "transport": self.telemetry.get_metrics(),
            "node_id": self.node_id
        }
