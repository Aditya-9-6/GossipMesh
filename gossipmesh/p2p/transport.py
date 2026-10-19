import asyncio
import logging
import struct
import json
from typing import Any, Callable, Dict, Optional, Union

from gossipmesh.p2p.dedup import GossipDedupFilter
from gossipmesh.p2p.reputation import LeakyBucketReputation


class RateLimitConfig:
    def __init__(self, burst_capacity: float = 10.0, max_rate_per_sec: float = 5.0) -> None:
        self.burst_capacity = burst_capacity
        self.max_rate_per_sec = max_rate_per_sec


class PeerRateLimiter:
    def __init__(self, config: Optional[RateLimitConfig] = None) -> None:
        self.config = config or RateLimitConfig()
        self._tokens: Dict[str, float] = {}
        self._last_check: Dict[str, float] = {}
        import time
        self._time_func = time.time
        self._lock = asyncio.Lock()

    async def allow(self, peer_id: str) -> bool:
        return self.check_rate_limit(peer_id)

    def check_rate_limit(self, peer_id: str) -> bool:
        now = self._time_func()
        tokens = self._tokens.get(peer_id, self.config.burst_capacity)
        last = self._last_check.get(peer_id, now)
        elapsed = max(0.0, now - last)
        
        tokens = min(self.config.burst_capacity, tokens + elapsed * self.config.max_rate_per_sec)
        self._last_check[peer_id] = now
        
        if tokens >= 1.0:
            self._tokens[peer_id] = tokens - 1.0
            return True
        self._tokens[peer_id] = tokens
        return False

    async def get_metrics(self) -> Dict[str, Any]:
        return {"burst_capacity": self.config.burst_capacity, "max_rate_per_sec": self.config.max_rate_per_sec}


class TransportTelemetry:
    def __init__(self) -> None:
        self.dropped_count = 0

    def record_dropped(self) -> None:
        self.dropped_count += 1


class GossipTransport:
    def __init__(self, node_id: str, config: Optional[RateLimitConfig] = None) -> None:
        self.node_id = node_id
        self.rate_limiter = PeerRateLimiter(config)
        self.reputation = LeakyBucketReputation()
        self.dedup = GossipDedupFilter()
        self._handlers: Dict[str, Callable[[Any], Any]] = {}
        self.telemetry = TransportTelemetry()

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        self._handlers[topic] = handler

    async def receive_payload(self, peer_id: str, payload: Union[bytes, str, dict, int], topic: str = 'default') -> Optional[Any]:
        if self.reputation.is_quarantined(peer_id):
            self.telemetry.record_dropped()
            logging.warning(f"Dropped payload from quarantined peer {peer_id}")
            return None
    
        allowed = self.rate_limiter.check_rate_limit(peer_id)
        if not allowed:
            self.telemetry.record_dropped()
            self.reputation.add_penalty(peer_id, 10.0)
            return None

        if isinstance(payload, bytes):
            try:
                payload_str = payload.decode('utf-8')
                try:
                    payload = json.loads(payload_str)
                except Exception:
                    payload = payload_str
            except Exception:
                pass

        handler = self._handlers.get(topic)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(payload)
                else:
                    return handler(payload)
            except Exception as e:
                logging.error(f"Handler exception for topic {topic}: {e}")
                return None
        return payload

    def record_received(self, size: int) -> None:
        pass


class EphemeralSessionKeyRotator:
    def get_public_bytes(self) -> bytes:
        return b"dummy_pub_key_bytes"


class P2PSessionTransport:
    def __init__(self, max_messages: int = 5, max_time_seconds: float = 60.0) -> None:
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds

    def initialize_session(self, pub_bytes: bytes) -> None:
        pass


class ZeroCopyPacketParser:
    @staticmethod
    def serialize_header(magic: int, msg_type: int, msg_id: str, payload: bytes) -> bytes:
        id_bytes = msg_id.encode('utf-8').ljust(36, b'\x00')[:36]
        length = len(payload)
        header = struct.pack(">I B 36s I", magic, msg_type, id_bytes, length)
        return header + payload

    @staticmethod
    def parse_header(buf: memoryview):
        if len(buf) < 45:
            raise ValueError("Buffer too small for packet header")
        magic, msg_type, raw_id, length = struct.unpack_from(">I B 36s I", buf, 0)
        msg_id = raw_id.rstrip(b'\x00').decode('utf-8')
        payload = buf[45:45 + length].tobytes()
        return magic, msg_type, msg_id, length, payload


class TransportSocketReader:
    def __init__(self, reader: asyncio.StreamReader, expected_magic: int = 0x474D4553) -> None:
        self.reader = reader
        self.expected_magic = expected_magic

    async def read_packet(self) -> tuple[int, int, str, int, bytes]:
        header_data = await self.reader.readexactly(45)
        buf = memoryview(header_data)
        magic, msg_type, msg_id, length, _ = ZeroCopyPacketParser.parse_header(buf)
        if magic != self.expected_magic:
            raise ValueError(f"Invalid magic header: {hex(magic)}")
        payload = await self.reader.readexactly(length)
        return magic, msg_type, msg_id, length, payload
