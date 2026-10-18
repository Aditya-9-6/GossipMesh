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

class TransportSocketReader:
    """Asynchronous socket reader supporting zero-copy parsing of P2P gossip packets."""
    
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 0x474D4553) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        # Read header size: magic(4) + type(1) + uuid(36) + length(4) = 45 bytes
        header_bytes = await self.reader.readexactly(45)
        buf = memoryview(header_bytes)
        magic, msg_type, msg_id, payload_len, payload_view = ZeroCopyPacketParser.parse_header(buf)
        
        if magic != self.expected_magic:
            raise ValueError(f"Invalid packet magic: 0x{magic:08X}, expected 0x{self.expected_magic:08X}")

        actual_payload_bytes = await self.reader.readexactly(payload_len)
        return msg_type, msg_id, memoryview(actual_payload_bytes)


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
            return encrypt_payload(plaintext, self.rotator.get_current_key())

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
                "bytes_received": self.bytes_received
            }


class GossipTransport:
    """Robust P2P Gossip Transport supporting erasure coding, rate-limiting, thread-safe fragment assembly, and topic multiplexing."""
    
    def __init__(
        self,
        node_id: str,
        k: int = 4,
        m: int = 2,
        block_size: int = 1024,
        config: Optional[RateLimitConfig] = None
    ) -> None:
        self.node_id = node_id
        self.k = k
        self.m = m
        self.block_size = block_size
        self.erasure_coder = ErasureCoder(k=k, m=m, block_size=block_size)
        self.rate_limiter = PeerRateLimiter(config=config)
        self.telemetry = TransportTelemetry()
        self.handlers: Dict[str, Callable[[Any], None]] = {}
        # Fragment assembler with thread-safe lock and TTL tracking (msg_id -> (timestamp, list of fragments, original_size))
        self.fragment_assembler: Dict[str, Tuple[float, List[Tuple[int, bytes]], int]] = {}
        self._assembler_lock = threading.Lock()

    def register_handler(self, topic: str, handler: Callable[[Any], None]) -> None:
        self.handlers[topic] = handler

    def _clean_expired_fragments_unlocked(self, ttl: float = 60.0) -> None:
        now = time.time()
        expired = [msg_id for msg_id, (timestamp, _, _) in self.fragment_assembler.items() if now - timestamp > ttl]
        for msg_id in expired:
            del self.fragment_assembler[msg_id]

    def add_fragment(self, msg_id: str, frag_idx: int, frag_data: bytes, original_size: Optional[int] = None, ttl: float = 60.0) -> Optional[bytes]:
        with self._assembler_lock:
            self._clean_expired_fragments_unlocked(ttl=ttl)
            if msg_id not in self.fragment_assembler:
                self.fragment_assembler[msg_id] = (time.time(), [], original_size or (self.k * self.block_size))
            
            timestamp, frags, orig_sz = self.fragment_assembler[msg_id]
            if not any(f[0] == frag_idx for f in frags):
                frags.append((frag_idx, frag_data))

            if len(frags) >= self.k:
                try:
                    reconstructed = self.erasure_coder.decode(frags, original_size=orig_sz)
                    del self.fragment_assembler[msg_id]
                    return reconstructed
                except Exception as e:
                    logger.warning("Failed to decode fragments for msg %s: %s", msg_id, e)
            return None

    async def send_payload(
        self, peer_id: str, payload: Union[bytes, str, dict], use_erasure: bool = False
    ) -> bool:
        if isinstance(payload, dict):
            payload_bytes = json.dumps(payload).encode('utf-8')
        elif isinstance(payload, str):
            payload_bytes = payload.encode('utf-8')
        else:
            payload_bytes = payload

        total_size = 0
        if use_erasure:
            fragments = self.erasure_coder.encode(payload_bytes)
            for frag_idx, frag_data in fragments:
                packet_size = len(frag_data) + 64
                total_size += packet_size
        else:
            total_size = len(payload_bytes) + 32

        self.telemetry.record_sent(total_size)
        return True

    async def receive_payload(
        self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str = 'default'
    ) -> Optional[Any]:
        if not self.rate_limiter.allow(peer_id):
            self.telemetry.record_dropped()
            return None

        if isinstance(payload, bytes):
            try:
                parsed = json.loads(payload.decode('utf-8'))
            except Exception:
                parsed = payload
        else:
            parsed = payload

        self.telemetry.record_received(len(str(parsed)))

        if topic in self.handlers:
            try:
                res = self.handlers[topic](parsed)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.exception("Error in message handler for topic %s: %s", topic, e)
        return parsed

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        metrics = self.telemetry.to_dict()
        metrics["rate_limiter_stats"] = self.rate_limiter.get_stats()
        return metrics