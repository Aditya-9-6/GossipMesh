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
        self.rotator = EphemeralSessionKeyRotator()
        self.max_messages = max_messages
        self.max_time_seconds = max_time_seconds
        self._lock = threading.Lock()
        self.creation_time = time.time()

    def initialize_session(self, peer_public_bytes: bytes):
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


class WindowedEMABandwidthThrottler:
    """Windowed Exponential Moving Average (EMA) bandwidth tracker and rate limiter.
    Calculates rolling byte rates over sliding time windows and enforces traffic shaping
    via a token bucket algorithm (<60 LOC per function)."""

    def __init__(self, max_bytes_per_sec: float, alpha: float = 0.3, burst_multiplier: float = 2.0):
        self.max_bytes_per_sec = float(max_bytes_per_sec)
        self.alpha = float(alpha)
        self.capacity = float(max_bytes_per_sec * burst_multiplier)
        self.tokens = self.capacity
        self.ema_rate = 0.0
        self.last_update = time.time()
        self._lock = threading.Lock()

    def update_and_check(self, bytes_transferred: int) -> bool:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now

            # Refill token bucket
            if elapsed > 0:
                self.tokens = min(self.capacity, self.tokens + elapsed * self.max_bytes_per_sec)

            # Update EMA byte rate
            instantaneous_rate = bytes_transferred / elapsed if elapsed > 0 else float(bytes_transferred)
            if self.ema_rate == 0.0:
                self.ema_rate = instantaneous_rate
            else:
                self.ema_rate = self.alpha * instantaneous_rate + (1 - self.alpha) * self.ema_rate

            # Enforce token bucket limit
            if self.tokens >= bytes_transferred:
                self.tokens -= bytes_transferred
                return True
            return False

    def get_current_rate(self) -> float:
        with self._lock:
            return self.ema_rate


class TransportTelemetry:
    """Telemetry tracking metrics for gossip transport layer."""

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
    """High-level P2P gossip transport integrating rate limiting, framing, and topic dispatch."""

    pass
