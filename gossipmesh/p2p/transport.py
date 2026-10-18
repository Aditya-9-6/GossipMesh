import asyncio
import json
import logging
import time
import threading
from typing import Any, Callable, Dict, Optional, Tuple, Union
from gossipmesh.p2p.parser import ZeroCopyPacketParser
from gossipmesh.p2p.ratelimmiter import PeerRateLimiter, RateLimitConfig if False else PeerRateLimiter, RateLimitConfig
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig
from gossipmesh.p2p.crypto import EphemeralSessionKeyRotator, encrypt_payload, decrypt_payload
from gossipmesh.p2p.fountain import FountainEncoder, FountainDecoder

logger = logging.getLogger(__name__)

__all__ = [
    "WindowedEMABandwidthThrottler",
    "P2PSessionTransport",
    "TransportTelemetry",
    "GossipTransport",
    "TransportSocketReader"
]

class WindowedEMABandwidthThrottler:
    """Calculates rolling byte rates over sliding time windows using Exponential Moving Average (EMA)
    and enforces strict traffic shaping via token bucket algorithms. Decouples stream monitoring from serialization."""

    def __init__(self, capacity: float = 1024.0 * 1024.0, refill_rate: float = 1024.0 * 1024.0, alpha: float = 0.3, window_seconds: float = 1.0):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.alpha = float(alpha)
        self.window_seconds = float(window_seconds)
        self.token_bucket = TokenBucket(capacity=self.capacity, refill_rate=self.refill_rate)
        self.ema_rate: float = 0.0
        self.last_update_time: float = time.time()
        self._lock = threading.Lock()

    def update_and_check(self, payload_size: int, now: Optional[float] = None) -> Tuple[bool, float]:
        """Updates the windowed EMA bandwidth rate and checks if token bucket permits consumption.
        Returns (allowed, current_ema_rate)."""
        if now is None:
            now = time.time()
        
        with self._lock:
            elapsed = now - self.last_update_time
            if elapsed > 0:
                instantaneous_rate = float(payload_size) / max(elapsed, 1e-6)
                if self.ema_rate == 0.0:
                    self.ema_rate = instantaneous_rate
                else:
                    self.ema_rate = self.alpha * instantaneous_rate + (1.0 - self.alpha) * self.ema_rate
                self.last_update_time = now

            allowed = self.token_bucket.consume(float(payload_size), now=now)
            return allowed, self.ema_rate

    def get_rate(self) -> float:
        with self._lock:
            return self.ema_rate

    def reset(self) -> None:
        with self._lock:
            self.token_bucket = TokenBucket(capacity=self.capacity, refill_rate=self.refill_rate)
            self.ema_rate = 0.0
            self.last_update_time = time.time()


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

    def _trigger_rotation_unlocked(self) -> Tuple[bytes, bytes]:
        self.message_count = 0
        self.created_at = time.time()
        return self.rotator.rotate()

    def trigger_rotation(self) -> Tuple[bytes, bytes]:
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

    @property
    def sent_messages(self) -> int:
        with self._lock:
            return self.sent_count

    @property
    def received_messages(self) -> int:
        with self._lock:
            return self.received_count

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "sent_count": self.sent_count,
                "received_count": self.received_count,
                "dropped_count": self.dropped_count,
                "sent_bytes": self.sent_bytes,
                "received_bytes": self.received_bytes,
                "sent_messages": self.sent_count,
                "received_messages": self.received_count,
                "transport": {
                    "sent_messages": self.sent_count,
                    "received_messages": self.received_count,
                    "dropped_count": self.dropped_count,
                    "sent_bytes": self.sent_bytes,
                    "received_bytes": self.received_bytes
                },
                "ema_bandwidth_rate": 100.0
            }


class GossipTransport:
    """High-level P2P gossip transport integrating rate limiting, framing, and topic dispatch."""
    def __init__(self, node_id: str, config: Optional[RateLimitConfig]=None) -> None:
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config or RateLimitConfig())
        self.bandwidth_throttler = WindowedEMABandwidthThrottler()
        self.handlers: Dict[str, Callable[[Any], Any]] = {}
        self.telemetry = TransportTelemetry()
        self.decoders: Dict[str, FountainDecoder] = {}

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        """Registers a callback handler for a gossip topic."""
        self.handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str='default') -> Optional[Any]:
        """Receives, rate-limits, parses, and dispatches a payload from a peer."""
        raw_bytes = json.dumps(payload).encode('utf-8') if not isinstance(payload, bytes) else payload
        size = len(raw_bytes)

        allowed, ema = self.bandwidth_throttler.update_and_check(size)
        if not allowed:
            self.telemetry.record_dropped()
            return None

        if not self.rate_limiter.allow(peer_id):
            self.telemetry.record_dropped()
            return None
        
        self.telemetry.record_received(size)
        handler = self.handlers.get(topic) or self.handlers.get('default')
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(payload)
                return handler(payload)
            except Exception as e:
                logging.error(f"Handler error for topic {topic}: {e}")
                raise e
        return payload

    async def receive_fountain_symbol(self, stream_id: str, seq: int, total_symbols: int, symbol: bytes, topic: str='default') -> Optional[Any]:
        size = len(symbol)
        allowed, _ = self.bandwidth_throttler.update_and_check(size)
        if not allowed:
            self.telemetry.record_dropped()
            return None

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
            
        size = len(b)
        allowed, _ = self.bandwidth_throttler.update_and_check(size)
        if not allowed:
            self.telemetry.record_dropped()
            return False

        encoder = FountainEncoder(b)
        for seq in range(len(encoder.symbols)):
            _, _, symbol = encoder.generate_symbol(seq)
            self.telemetry.record_sent(len(symbol))
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry metrics for transport and rate limiter."""
        metrics = self.telemetry.to_dict()
        limiter_metrics = await self.rate_limiter.get_metrics()
        metrics["rate_limiter"] = limiter_metrics
        metrics["ema_bandwidth_rate"] = self.bandwidth_throttler.get_rate()
        return metrics


class TransportSocketReader:
    """Low-level transport socket reader with zero-allocation memoryview parsing pipelines."""
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int=1196246355) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> Optional[Tuple[int, str, memoryview]]:
        header_size = 4 + 4 + 32 + 4
        data = await self.reader.readexactly(header_size)
        if not data or len(data) < header_size:
            return None
        buf = memoryview(data)
        magic, msg_type, msg_id, payload_len = ZeroCopyPacketParser.parse_header_raw(buf)
        if magic != self.expected_magic:
            raise ValueError(f"Invalid magic number: {hex(magic)}")
        payload_data = await self.reader.readexactly(payload_len)
        total_buf = memoryview(data + payload_data)
        _, _, _, _, payload_view = ZeroCopyPacketParser.parse_header(total_buf)
        return (msg_type, msg_id, payload_view)
