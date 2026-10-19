import asyncio
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from gossipmesh.p2p.crypto import EphemeralSessionKeyRotator, decrypt_payload, encrypt_payload
from gossipmesh.p2p.erasure import ErasureCoder
from gossipmesh.p2p.parser import ZeroCopyPacketParser
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)


def _serialize_to_raw_bytes(payload: Any) -> bytes:
    """Converts varied payload formats to raw UTF-8 bytes."""
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    if isinstance(payload, dict):
        return json.dumps(payload).encode("utf-8")
    return str(payload).encode("utf-8")


def _parse_incoming_payload(payload: Any) -> Any:
    """Parses incoming raw data or object into dispatch-ready payload format."""
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, bytes):
        try:
            return json.loads(payload.decode("utf-8", errors="ignore"))
        except Exception:
            return {"raw": payload.decode("utf-8", errors="ignore")}
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except Exception:
            return {"raw": payload}
    if isinstance(payload, (int, float, list)):
        return {"data": payload}
    return {"data": str(payload)}


class TransportTelemetry:
    """Telemetry tracking metrics for gossip transport layer messaging and bandwidth."""

    def __init__(self) -> None:
        self.sent_messages: int = 0
        self.received_messages: int = 0
        self.sent_bytes: int = 0
        self.received_bytes: int = 0
        self.dropped_messages: int = 0

    def record_sent(self, size_bytes: int) -> None:
        self.sent_messages += 1
        self.sent_bytes += size_bytes

    def record_received(self, size_bytes: int) -> None:
        self.received_messages += 1
        self.received_bytes += size_bytes

    def record_dropped(self) -> None:
        self.dropped_messages += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sent_messages": self.sent_messages,
            "received_messages": self.received_messages,
            "sent_bytes": self.sent_bytes,
            "received_bytes": self.received_bytes,
            "dropped_messages": self.dropped_messages,
        }


class GossipTransport:
    """Async P2P Transport Layer with rate-limiting, backpressure protection, and payload dispatch."""

    def __init__(
        self,
        node_id: str,
        config: Optional[RateLimitConfig] = None,
    ) -> None:
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config=config or RateLimitConfig())
        self.telemetry = TransportTelemetry()
        self.handlers: Dict[str, Callable[[Any], Any]] = {}

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        """Registers a callback handler for a gossip topic."""
        self.handlers[topic] = handler

    async def receive_payload(
        self, peer_id: str, payload: Union[bytes, str, dict, int, float, list, Any], topic: str = "default"
    ) -> Optional[Any]:
        """Receives, rate-limits, parses, and dispatches a payload from a peer."""
        raw_bytes = _serialize_to_raw_bytes(payload)
        size_bytes = len(raw_bytes)
        allowed, _reason = await self.rate_limiter.check_and_consume(peer_id, size_bytes)
        if not allowed:
            self.telemetry.record_dropped()
            return None

        self.telemetry.record_received(size_bytes)
        parsed_data = _parse_incoming_payload(payload)

        if topic in self.handlers:
            try:
                res = self.handlers[topic](parsed_data)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.error(f"Error in transport handler for topic {topic}: {e}")

        return parsed_data

    async def send_payload(self, peer_id: str, payload: Union[bytes, str, dict, Any]) -> bool:
        """Simulates sending a payload to a peer with telemetry recording."""
        raw_bytes = _serialize_to_raw_bytes(payload)
        self.telemetry.record_sent(len(raw_bytes))
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry metrics for transport and rate limiter."""
        limiter_metrics = await self.rate_limiter.get_metrics()
        return {
            "transport": self.telemetry.to_dict(),
            "rate_limiter": limiter_metrics,
        }


class P2PSessionTransport(GossipTransport):
    """Session-secured wrapper around GossipTransport with ephemeral key rotation."""

    def __init__(
        self,
        node_id: str = "default",
        config: Optional[RateLimitConfig] = None,
        max_messages: int = 1000,
        max_time_seconds: float = 3600.0,
    ) -> None:
        super().__init__(node_id=node_id, config=config)
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self.rotator = EphemeralSessionKeyRotator()
        self._lock = threading.Lock()
        self.creation_time = time.time()

    def initialize_session(self, peer_public_bytes: bytes) -> None:
        with self._lock:
            self.rotator.derive_session_key(peer_public_bytes)
            self.creation_time = time.time()

    def _should_rotation_unlocked(self) -> bool:
        if self.rotator.message_counter >= self.max_messages:
            return True
        if (time.time() - self.creation_time) >= self.max_time_seconds:
            return True
        return False

    def should_rotate(self) -> bool:
        with self._lock:
            return self._should_rotation_unlocked()

    def _trigger_rotation_unlocked(self) -> bytes:
        _, new_pub_bytes = self.rotator.rotate()
        self.creation_time = time.time()
        return new_pub_bytes

    def trigger_rotation(self) -> bytes:
        with self._lock:
            return self._trigger_rotation_unlocked()

    def send_message(self, plaintext: bytes) -> bytes:
        with self._lock:
            if self._should_rotation_unlocked():
                self._trigger_rotation_unlocked()
            ciphertext = encrypt_payload(self.rotator.session_key, plaintext)
            self.rotator.message_counter += 1
            return ciphertext

    def receive_message(self, ciphertext: bytes) -> bytes:
        with self._lock:
            if self._should_rotation_unlocked():
                self._trigger_rotation_unlocked()
            plaintext = decrypt_payload(self.rotator.session_key, ciphertext)
            self.rotator.message_counter += 1
            return plaintext


class ErasureTransportMultiplexer:
    """Integrates erasure coding fragment multiplexing into gossip transport dissemination."""

    def __init__(self, k: int = 4, m: int = 2) -> None:
        self.coder = ErasureCoder(k=k, m=m)

    def prepare_dissemination(self, payload_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_data = json.dumps(payload_dict).encode("utf-8")
        original_size = len(raw_data)
        fragments = self.coder.encode(raw_data)

        dissemination_packets = []
        for shard_idx, shard_data in fragments:
            packet = {
                "shard_index": shard_idx,
                "k": self.coder.k,
                "m": self.coder.m,
                "original_size": original_size,
                "payload_shard": shard_data.hex(),
            }
            dissemination_packets.append(packet)
        return dissemination_packets

    def assemble_dissemination(self, packets: List[Dict[str, Any]]) -> Dict[str, Any]:
        fragments = []
        original_size = None
        for pkt in packets:
            idx = pkt["shard_index"]
            data = bytes.fromhex(pkt["payload_shard"])
            fragments.append((idx, data))
            if original_size is None:
                original_size = pkt.get("original_size")

        raw_bytes = self.coder.decode(fragments, original_size=original_size)
        return json.loads(raw_bytes.decode("utf-8"))


class TransportSocketReader:
    """Low-level transport socket reader with zero-allocation memoryview parsing pipelines."""

    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 0x474D4553) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        """Reads a full gossip packet from the stream and returns header metadata and memoryview payload."""
        try:
            header_data = await self.reader.readexactly(ZeroCopyPacketParser.HEADER_SIZE)
        except asyncio.IncompleteReadError:
            return None

        if not header_data:
            return None

        header_view = memoryview(header_data)
        magic, msg_type, msg_id, payload_len, _ = ZeroCopyPacketParser.parse_header(header_view)

        if magic != self.expected_magic:
            logger.warning(f"Invalid packet magic received: {hex(magic)}")
            raise ValueError(f"Invalid packet magic: {hex(magic)}")

        try:
            payload_data = await self.reader.readexactly(payload_len)
        except asyncio.IncompleteReadError as e:
            raise ValueError(
                f"Incomplete payload read: expected {payload_len} bytes, got {len(e.partial)}"
            )

        full_packet = header_data + payload_data
        full_view = memoryview(full_packet)
        _, _, _, _, payload_view = ZeroCopyPacketParser.parse_header(full_view)

        return msg_type, msg_id, payload_view
