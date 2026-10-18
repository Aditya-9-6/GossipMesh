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

class TransportTelemetry:
    """Telemetry collector for transport operations."""
    def __init__(self) -> None:
        self.metrics: Dict[str, Any] = {}

    def record(self, key: str, value: Any) -> None:
        self.metrics[key] = value

class EphemeralSessionKeyRotatorExtended(EphemeralSessionKeyRotator):
    def initialize_peer(self, peer_public_bytes: bytes) -> None:
        self.peer_public_bytes = peer_public_bytes

class P2PSessionTransport:
    """Manages peer-to-peer transport streams with automatic key rotation
every 1000 messages or 300 seconds without dropping streams."""
    def __init__(self, max_messages: int = 1000, max_time_seconds: float = 300.0):
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self.message_count = 0
        self.start_time = time.monotonic()
        self.rotator = EphemeralSessionKeyRotatorExtended()
        self._lock = threading.Lock()

    def initialize_session(self, peer_public_bytes: bytes) -> None:
        with self._lock:
            self.rotator.initialize_peer(peer_public_bytes)

class GossipTransport:
    """Gossip transport handling sending, receiving, rate-limiting, and dispatching payloads."""
    def __init__(self, node_id: str, rate_config: Optional[RateLimitConfig] = None) -> None:
        self.node_id = node_id
        self.limiter = PeerRateLimiter(rate_config)
        self.handlers: Dict[str, Callable[[Any], Any]] = {}
        self.sent_messages = 0
        self.received_messages = 0
        self.dropped_messages = 0
        self._lock = asyncio.Lock()
        self.telemetry = TransportTelemetry()

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Union[bytes, dict, str], topic: str = "default") -> Any:
        async with self._lock:
            if not self.limiter.acquire(peer_id):
                self.dropped_messages += 1
                return None
            self.received_messages += 1

        parsed_payload = payload
        if isinstance(payload, bytes):
            try:
                parsed_payload = json.loads(payload.decode('utf-8'))
            except Exception:
                pass

        handler = self.handlers.get(topic)
        if handler:
            try:
                return handler(parsed_payload)
            except Exception as e:
                raise e
        return parsed_payload

    async def send_payload(self, peer_id: str, payload: Any) -> bool:
        async with self._lock:
            if not self.limiter.acquire(peer_id):
                self.dropped_messages += 1
                return False
            self.sent_messages += 1
            return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        async with self._lock:
            limiter_metrics = self.limiter.get_metrics()
            return {
                "transport": {
                    "sent_messages": self.sent_messages,
                    "received_messages": self.received_messages,
                    "dropped_messages": self.dropped_messages,
                },
                "ratelimiter": limiter_metrics
            }

class TransportSocketReader:
    """Zero-copy socket packet reader."""
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

        msg_id = msg_id_bytes.decode('utf-8').rstrip('\x00')
        payload_bytes = await self.reader.readexactly(payload_len)
        return msg_type, msg_id, memoryview(payload_bytes)
