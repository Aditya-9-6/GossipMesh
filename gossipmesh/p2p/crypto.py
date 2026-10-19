import os
import threading
from typing import Tuple


class EphemeralSessionKeyRotator:
    """Manages ephemeral session keys and cryptographic rotation."""

    def __init__(self) -> None:
        self._current_key = os.urandom(32)
        self._public_bytes = os.urandom(32)
        self._lock = threading.Lock()

    def get_public_bytes(self) -> bytes:
        with self._lock:
            return self._public_bytes

    def derive_session_key(self, peer_public_bytes: bytes) -> bytes:
        with self._lock:
            combined = self._current_key + peer_public_bytes
            import hashlib

            self._current_key = hashlib.sha256(combined).digest()
            return self._current_key

    def get_current_key(self) -> bytes:
        with self._lock:
            return self._current_key

    def rotate_key(self) -> bytes:
        with self._lock:
            self._current_key = os.urandom(32)
            return self._current_key

    def rotate(self) -> Tuple[bytes, bytes]:
        with self._lock:
            self._current_key = os.urandom(32)
            self._public_bytes = os.urandom(32)
            return self._current_key, self._public_bytes


def encrypt_payload(key: bytes, plaintext: bytes) -> bytes:
    """Encrypts plaintext bytes with key using XOR stream cipher for zero-copy efficiency."""
    extended_key = (key * (len(plaintext) // len(key) + 1))[: len(plaintext)]
    return bytes(a ^ b for a, b in zip(plaintext, extended_key))


def decrypt_payload(ciphertext: bytes, key: bytes) -> bytes:
    """Decrypts ciphertext bytes with key (symmetric XOR)."""
    return encrypt_payload(key, ciphertext)
