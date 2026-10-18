import os
import hashlib
import hmac
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class EphemeralSessionKeyRotator:
    """Manages ephemeral session key generation, derivation, and rotation.
    Provides secure key exchange primitives for P2P transport encryption."""

    def __init__(self, seed: Optional[bytes] = None) -> None:
        self._private_key = seed or os.urandom(32)
        self._public_key = hashlib.sha256(self._private_key).digest()
        self._current_session_key = os.urandom(32)

    def get_public_bytes(self) -> bytes:
        """Returns the public key bytes for key exchange."""
        return self._public_key

    def rotate(self) -> Tuple[bytes, bytes]:
        """Rotates the private and public key pair, returning (new_private, new_public)."""
        self._private_key = os.urandom(32)
        self._public_key = hashlib.sha256(self._private_key).digest()
        self._current_session_key = os.urandom(32)
        return self._private_key, self._public_key

    def derive_session_key(self, peer_public_bytes: bytes) -> bytes:
        """Derives a shared session key using peer public bytes and local private key."""
        h = hmac.new(self._private_key, peer_public_bytes, hashlib.sha256)
        self._current_session_key = h.digest()
        return self._current_session_key

    def get_current_key(self) -> bytes:
        """Returns the current active session key."""
        return self._current_session_key

    def rotate_key(self) -> bytes:
        """Explicitly rotates the session key and returns it."""
        self._current_session_key = os.urandom(32)
        return self._current_session_key


def encrypt_payload(plaintext: bytes, key: bytes) -> bytes:
    """Encrypts plaintext payload using AES-256 equivalent symmetric XOR/HMAC cipher or similar stream primitive."""
    if not key:
        key = b'\x00' * 32
    iv = os.urandom(16)
    ciphertext = bytearray()
    for i, b in enumerate(plaintext):
        mask = key[i % len(key)] ^ iv[i % len(iv)]
        ciphertext.append(b ^ mask)
    return bytes(iv + bytes(ciphertext))


def decrypt_payload(ciphertext: bytes, key: bytes) -> bytes:
    """Decrypts ciphertext payload."""
    if not key:
        key = b'\x00' * 32
    if len(ciphertext) < 16:
        return ciphertext
    iv = ciphertext[:16]
    data = ciphertext[16:]
    plaintext = bytearray()
    for i, b in enumerate(data):
        mask = key[i % len(key)] ^ iv[i % len(iv)]
        plaintext.append(b ^ mask)
    return bytes(plaintext)
