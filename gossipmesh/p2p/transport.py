import asyncio
import json
import logging
import struct
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
    def __init__(self, max_messages: int=1000, max_time_seconds: float=300.0):
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self.message_count = 0
        self.created_at = time.time()
        self.rotator = EphemeralSessionKeyRotator()
        self._lock = threading.Lock()

    def initialize_session(self, peer_public_bytes: bytes):
        with self._lock:
            self.rotator.derive_shared_secret(peer_public_bytes)

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
        return self.rotator.rotate()

    def trigger_rotation(self) -> bytes:
        with self._lock:
            return self._trigger_rotation_unlocked()

    def send_message(self, plaintext: bytes) -> bytes:
        with self._lock:
            self.message_count += 1
            if self._should_rotation_unlocked():
                self._trigger_rotation_unlocked()
            return encrypt_payload(self.rotator.current_key, plaintext)

    def receive_message(self, ciphertext: bytes) -> bytes:
        with self._lock:
            self.message_count += 1
            if self._should_rotation_unlocked():
                self._trigger_rotation_unlocked()
            return decrypt_payload(self.rotator.current_key, ciphertext)

class TransportTelemetry:
    """Telemetry tracking metrics for gossip transport layer."""
    def __init__(self) -> None:
        self.sent_count = 0
        self.received_count = 0
        self.dropped_count = 0
        self.sent_bytes = 0
        self.received_bytes = 0
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
                "transport": {
                    "sent_messages": self.sent_count,
                    "received_messages": self.received_count,
                    "dropped_messages": self.dropped_count,
                    "sent_bytes": self.sent_bytes,
                    "received_bytes": self.received_bytes
                },
                "sent_count": self.sent_count,
                "received_count": self.received_count,
                "dropped_count": self.dropped_count,
                "sent_bytes": self.sent_bytes,
                "received_bytes": self.received_bytes
            }

class GossipTransport:
    """High-level P2P gossip transport integrating rate limiting, framing, and topic dispatch."""
    def __init__(self, node_id: str, config: Optional[RateLimitConfig]=None) -> None:
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config or RateLimitConfig())
        self.handlers: Dict[str, Callable[[Any], Any]] = {}
        self.telemetry = TransportTelemetry()
        self.decoders: Dict[str, FountainDecoder] = {}

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        """Registers a callback handler for a gossip topic."""
        self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str='default') -> Optional[Any]:
        """Receives, rate-limits, parses, and dispatches a payload from a peer."""
        if not self.rate_limiter.allow(peer_id):
            self.telemetry.record_dropped()
            return None
        
        if isinstance(payload, (dict, list)):
            payload_bytes = json.dumps(payload).encode('utf-8')
        elif isinstance(payload, str):
            payload_bytes = payload.encode('utf-8')
        elif isinstance(payload, bytes):
            payload_bytes = payload
        elif isinstance(payload, int):
            payload_bytes = str(payload).encode('utf-8')
        else:
            payload_bytes = str(payload).encode('utf-8')
            
        self.telemetry.record_received(len(payload_bytes))
        handler = self.handlers.get(topic)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(payload)
                return handler(payload)
            except Exception:
                logging.exception("Error in message handler for topic %s", topic)
                return None
        return payload

    async def receive_fountain_symbol(self, stream_id: str, seq: int, total_symbols: int, symbol: bytes, topic: str='default') -> Optional[Any]:
        if stream_id not in self.decoders:
            self.decoders[stream_id] = FountainDecoder(total_symbols)
        decoder = self.decoders[stream_id]
        complete = decoder.add_symbol(seq, symbol)
        if complete:
            decoded_data = decoder.decode()
            del self.decoders[stream_id]
            if decoded_data:
                try:
                    parsed = json.loads(decoded_data.decode('utf-8'))
                    return await self.receive_payload(stream_id, parsed, topic)
                except Exception:
                    return await self.receive_payload(stream_id, decoded_data, topic)
        return None

    async def send_payload(self, peer_id: str, payload: Union[bytes, str, dict]) -> bool:
        """Simulates sending a payload to a peer with telemetry recording."""
        if isinstance(payload, (dict, list)):
            b = json.dumps(payload).encode('utf-8')
        elif isinstance(payload, str):
            b = payload.encode('utf-8')
        elif isinstance(payload, bytes):
            b = payload
        else:
            b = str(payload).encode('utf-8')
            
        encoder = FountainEncoder(b)
        for seq in range(len(encoder.symbols)):
            _, _, symbol = encoder.generate_symbol(seq)
            self.telemetry.record_sent(len(symbol))
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
        try:
            header_data = await self.reader.readexactly(12)
            if len(header_data) < 12:
                return None
            magic, length, flags = struct.unpack(">III", header_data)
            if magic != self.expected_magic:
                raise ValueError(f"Invalid packet magic: {hex(magic)}, expected {hex(self.expected_magic)}")
            
            msg_id_bytes = await self.reader.readexactly(32)
            msg_id = msg_id_bytes.rstrip(b'\x00').decode('utf-8', errors='ignore')
            
            payload_bytes = await self.reader.readexactly(length)
            return (flags, msg_id, memoryview(payload_bytes))
        except asyncio.IncompleteReadError:
            return None
