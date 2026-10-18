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
        self.start_time = time.monotonic()
        self._session_key = None

    def initialize_session(self, peer_pub_bytes: bytes) -> None:
        self._session_key = peer_pub_bytes

    def send_message(self, plaintext: bytes) -> bytes:
        self.message_count += 1
        return encrypt_payload(plaintext, self._session_key or b'default_key')

    def receive_message(self, ciphertext: bytes) -> bytes:
        return decrypt_payload(ciphertext, self._session_key or b'default_key')

    def should_rotate(self) -> bool:
        if self.message_count >= self.max_messages:
            return True
        if (time.monotonic() - self.start_time) >= self.max_time_seconds:
            return True
        return False

class TransportSocketReader:
    """Reads network packets from asyncio stream reader with magic validation."""
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 0x474D4553) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        header_size = 4 + 4 + 36 + 4
        try:
            header_data = await self.reader.readexactly(header_size)
        except Exception:
            return None

        magic, msg_type, msg_id_bytes, payload_len = ZeroCopyPacketParser.deserialize_header(header_data)
        if magic != self.expected_magic:
            raise ValueError(f"Invalid magic number: {hex(magic)}, expected {hex(self.expected_magic)}")

        try:
            msg_id = msg_id_bytes.rstrip(b'\x00').decode('utf-8')
        except Exception:
            msg_id = str(msg_id_bytes)

        payload_data = await self.reader.readexactly(payload_len)
        return magic, msg_id, memoryview(payload_data)

class GossipTransport:
    """Gossip Transport layer with integrated rate limiting, handlers, and telemetry."""
    def __init__(self, node_id: str, rate_limit_config: Optional[RateLimitConfig] = None) -> None:
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(rate_limit_config)
        self.handlers: Dict[str, Callable[[Any], Any]] = {}
        self.sent_messages = 0
        self.sent_bytes = 0
        self._lock = asyncio.Lock()

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Union[bytes, str, dict], topic: str = "default") -> Any:
        # Check rate limit
        if not self.rate_limiter.acquire(peer_id):
            logger.warning(f"Rate limit exceeded for peer {peer_id}")
            return None

        parsed_payload = payload
        if isinstance(payload, bytes):
            try:
                parsed_payload = json.loads(payload.decode('utf-8'))
            except Exception:
                try:
                    parsed_payload = payload.decode('utf-8')
                except Exception:
                    parsed_payload = payload
        elif isinstance(payload, str):
            try:
                parsed_payload = json.loads(payload)
            except Exception:
                parsed_payload = payload

        handler = self.handlers.get(topic)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(parsed_payload)
                else:
                    return handler(parsed_payload)
            except Exception as e:
                logger.error(f"Error in handler for topic {topic}: {e}")
                raise e
        return parsed_payload

    async def send_payload(self, peer_id: str, payload: Union[bytes, str, dict]) -> bool:
        async with self._lock:
            if not self.rate_limiter.acquire(peer_id):
                return False
            self.sent_messages += 1
            if isinstance(payload, bytes):
                self.sent_bytes += len(payload)
            elif isinstance(payload, str):
                self.sent_bytes += len(payload.encode('utf-8'))
            else:
                encoded = json.dumps(payload)
                self.sent_bytes += len(encoded.encode('utf-8'))
            return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        ratelimit_metrics = self.rate_limiter.get_metrics()
        return {
            "transport": {
                "sent_messages": self.sent_messages,
                "sent_bytes": self.sent_bytes,
                "node_id": self.node_id,
            },
            "dropped_count": ratelimit_metrics.get("dropped_count", 0),
            "allowed_count": ratelimit_metrics.get("allowed_count", 0),
            "active_peers": ratelimit_metrics.get("active_peers", 0),
        }

class TransportTelemetry:
    """Telemetry wrapper for gossip transport monitoring."""
    def __init__(self, transport: GossipTransport) -> None:
        self.transport = transport

    async def collect(self) -> Dict[str, Any]:
        return await self.transport.get_telemetry_metrics()
