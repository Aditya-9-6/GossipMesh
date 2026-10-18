import time
import threading
from typing import Optional, Callable, Dict, Any
from gossipmesh.p2p.crypto import EphemeralSessionKeyRotator, encrypt_payload, decrypt_payload
from gossipmesh.p2p.ratelimit import PeerRateLimiter, RateLimitConfig

class TransportTelemetry:
    """Telemetry metrics collector for GossipTransport."""
    def __init__(self):
        self.received_messages = 0
        self.sent_messages = 0
        self.dropped_messages = 0
        self.sent_bytes = 0

class GossipTransport:
    """Manages peer-to-peer transport streams, rate limiting, and session key rotation."""
    def __init__(self, node_id: str, max_messages: int = 1000, max_time_seconds: float = 300.0, config: Optional[RateLimitConfig] = None):
        self.node_id = node_id
        self.rotator = EphemeralSessionKeyRotator()
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self.rate_limiter = PeerRateLimiter(config=config or RateLimitConfig())
        self.handlers: Dict[str, Callable[[Any], Any]] = {}
        self.telemetry = TransportTelemetry()
        self._lock = threading.Lock()
        self.creation_time = time.time()

    def register_handler(self, topic: str, handler: Callable[[Any], Any]) -> None:
        self.handlers[topic] = handler

    def initialize_session(self, peer_public_bytes: bytes):
        with self._lock:
            self.rotator.derive_session_key(peer_public_bytes)
            self.creation_time = time.time()

    def should_rotate(self) -> bool:
        with self._lock:
            if self.rotator.message_counter >= self.max_messages:
                return True
            if (time.time() - self.creation_time) >= self.max_time_seconds:
                return True
            return False

    def trigger_rotation(self) -> bytes:
        with self._lock:
            _, new_pub_bytes = self.rotator.rotate()
            self.creation_time = time.time()
            return new_pub_bytes

    def send_message(self, plaintext: bytes) -> bytes:
        with self._lock:
            if self.should_rotate():
                self.trigger_rotation()
            if not self.rotator.session_key:
                raise ValueError("Session key not established for P2P transport.")
            
            self.rotator.message_counter += 1
            return encrypt_payload(self.rotator.session_key, plaintext)

    def receive_message(self, ciphertext_with_nonce: bytes) -> bytes:
        with self._lock:
            if self.should_rotate():
                self.trigger_rotation()
            if not self.rotator.session_key:
                raise ValueError("Session key not established for P2P transport.")
            
            self.rotator.message_counter += 1
            return decrypt_payload(self.rotator.session_key, ciphertext_with_nonce)

    async def receive_payload(self, peer_id: str, payload: Any, topic: str = "default") -> Optional[Any]:
        import json
        byte_size = len(str(payload).encode('utf-8'))
        allowed, _ = await self.rate_limiter.check_and_consume(peer_id, byte_size)
        if not allowed:
            self.telemetry.dropped_messages += 1
            return None

        self.telemetry.received_messages += 1
        
        parsed_payload = payload
        if isinstance(payload, bytes):
            try:
                parsed_payload = json.loads(payload.decode('utf-8'))
            except Exception:
                parsed_payload = {"raw": payload.decode('utf-8', errors='ignore')}
        elif isinstance(payload, str):
            try:
                parsed_payload = json.loads(payload)
            except Exception:
                parsed_payload = {"raw": payload}
        elif isinstance(payload, (int, float)):
            parsed_payload = {"data": payload}

        if topic in self.handlers:
            try:
                res = self.handlers[topic](parsed_payload)
                if hasattr(res, '__await__'):
                    await res
            except Exception:
                pass

        return parsed_payload

    async def send_payload(self, peer_id: str, payload: Any) -> bool:
        self.telemetry.sent_messages += 1
        self.telemetry.sent_bytes += len(str(payload).encode('utf-8'))
        return True

    async def get_telemetry_metrics(self) -> Dict[str, Any]:
        limiter_metrics = await self.rate_limiter.get_metrics()
        return {
            "transport": {
                "received_messages": self.telemetry.received_messages,
                "sent_messages": self.telemetry.sent_messages,
                "dropped_messages": self.telemetry.dropped_messages,
                "sent_bytes": self.telemetry.sent_bytes,
            },
            "rate_limiter": limiter_metrics
        }
