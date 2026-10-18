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
    """High-level P2P gossip transport integrating rate limiting, framing, topic dispatch, and erasure coding multiplexing."""
    def __init__(self, node_id: str, config: Optional[RateLimitConfig]=None, k: int = 4, m: int = 2) -> None:
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config or RateLimitConfig())
        self.handlers: Dict[str, Callable[[Any], Any]] = {}
        self.telemetry = TransportTelemetry()
        self.erasure_coder = ErasureCoder(k=k, m=m)
        self.fragment_assembler: Dict[str, List[Tuple[int, bytes]]] = {}

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        """Registers a callback handler for a gossip topic."""
        self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str='default') -> Optional[Any]:
        """Receives, rate-limits, parses, and dispatches a payload from a peer, supporting erasure fragments."""
        if not self.rate_limiter.allow(peer_id):
            self.telemetry.record_dropped()
            logger.warning(f"Rate limit exceeded for peer {peer_id}")
            return None

        if isinstance(payload, dict) and "fragment_idx" in payload:
            # Handle erasure-coded fragment multiplexing
            msg_id = payload.get("msg_id", "default_msg")
            frag_idx = payload["fragment_idx"]
            frag_data = bytes.fromhex(payload["data"])
            
            if msg_id not in self.fragment_assembler:
                self.fragment_assembler[msg_id] = []
            
            self.fragment_assembler[msg_id].append((frag_idx, frag_data))
            self.telemetry.record_received(len(frag_data))
            
            if len(self.fragment_assembler[msg_id]) >= self.erasure_coder.k:
                fragments = self.fragment_assembler.pop(msg_id)
                reconstructed_bytes = self.erasure_coder.decode(fragments)
                try:
                    decoded_payload = json.loads(reconstructed_bytes.decode('utf-8'))
                except Exception:
                    decoded_payload = reconstructed_bytes
                
                handler = self.handlers.get(topic)
                if handler:
                    if asyncio.iscoroutinefunction(handler):
                        return await handler(decoded_payload)
                    return handler(decoded_payload)
                return decoded_payload
            return None

        data_bytes = json.dumps(payload).encode('utf-8') if not isinstance(payload, bytes) else payload
        self.telemetry.record_received(len(data_bytes))
        
        handler = self.handlers.get(topic)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                return await handler(payload)
            return handler(payload)
        return payload

    async def send_payload(self, peer_id: str, payload: Union[bytes, str, dict], use_erasure: bool = True) -> bool:
        """Simulates sending a payload to a peer with erasure coding multiplexing and telemetry recording."""
        data_bytes = json.dumps(payload).encode('utf-8') if not isinstance(payload, bytes) else payload
        
        if use_erasure:
            msg_id = f"{self.node_id}-{time.time_ns()}"
            fragments = self.erasure_coder.encode(data_bytes)
            total_sent = 0
            for frag_idx, frag_bytes in fragments:
                frag_payload = {
                    "msg_id": msg_id,
                    "fragment_idx": frag_idx,
                    "data": frag_bytes.hex()
                }
                serialized = json.dumps(frag_payload).encode('utf-8')
                total_sent += len(serialized)
            self.telemetry.record_sent(total_sent)
            return True
        else:
            self.telemetry.record_sent(len(data_bytes))
            return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry metrics for transport and rate limiter."""
        metrics = self.telemetry.to_dict()
        metrics["rate_limiter_stats"] = self.rate_limiter.get_stats()
        return metrics


class TransportSocketReader:
    """Low-level transport socket reader with zero-allocation memoryview parsing pipelines."""
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int=1196246355) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        """Reads a full gossip packet from the stream and returns header metadata and memoryview payload."""
        try:
            header = await self.reader.readexactly(12)
            if len(header) < 12:
                return None
            magic, length, msg_type = struct.unpack("!IHI", header[:10])
            if magic != self.expected_magic:
                return None
            body = await self.reader.readexactly(length)
            return (msg_type, "peer_stream", memoryview(body))
        except asyncio.CancelledError:
            raise
        except Exception:
            return None
