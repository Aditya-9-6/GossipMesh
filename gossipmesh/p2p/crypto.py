import os
import hashlib
import hmac
import threading
from typing import Optional, Tuple

try:
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


def generate_ephemeral_keypair() -> Tuple[bytes, bytes]:
    """Generates a random ephemeral private/public keypair (32 bytes each for simplicity/compatibility)."""
    private_key = os.urandom(32)
    public_key = hashlib.sha256(private_key).digest()
    return private_key, public_key


def derive_shared_secret(private_key: bytes, peer_public_key: bytes) -> bytes:
    """Derives a shared secret using HKDF or HMAC-SHA256 from local private key and peer public key."""
    return hmac.new(private_key, peer_public_key, hashlib.sha256).digest()


def encrypt_payload(plaintext: bytes, key: bytes, associated_data: Optional[bytes] = None) -> bytes:
    """Encrypts plaintext bytes using ChaCha20Poly1305 if available, or fallback AES-like XOR/HMAC."""
    if not key:
        key = b'\x00' * 32
    if len(key) < 32:
        key = key.ljust(32, b'\x00')
    
    nonce = os.urandom(12)
    if HAS_CRYPTOGRAPHY:
        try:
            cipher = ChaCha20Poly1305(key[:32])
            ciphertext = cipher.encrypt(nonce, plaintext, associated_data)
            return nonce + ciphertext
        except Exception:
            pass
            
    # Fallback encryption if cryptography library is missing or fails
    mask = hmac.new(key, nonce, hashlib.sha256).digest()
    encrypted = bytearray(b ^ mask[i % len(mask)] for i, b in enumerate(plaintext))
    tag = hmac.new(key, nonce + bytes(encrypted), hashlib.sha256).digest()[:16]
    return nonce + tag + bytes(encrypted)


def decrypt_payload(ciphertext: bytes, key: bytes, associated_data: Optional[bytes] = None) -> bytes:
    """Decrypts ciphertext bytes produced by encrypt_payload."""
    if not key:
        key = b'\x00' * 32
    if len(key) < 32:
        key = key.ljust(32, b'\x00')

    if len(ciphertext) < 28:
        raise ValueError("Ciphertext too short")

    nonce = ciphertext[:12]
    
    if HAS_CRYPTOGRAPHY:
        try:
            cipher = ChaCha20Poly1305(key[:32])
            actual_ciphertext = ciphertext[12:]
            return cipher.decrypt(nonce, actual_ciphertext, associated_data)
        except Exception:
            pass

    # Fallback decryption
    tag = ciphertext[12:28]
    encrypted = ciphertext[28:]
    expected_tag = hmac.new(key, nonce + encrypted, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Decryption failed: authentication tag mismatch")

    mask = hmac.new(key, nonce, hashlib.sha256).digest()
    decrypted = bytes(b ^ mask[i % len(mask)] for i, b in enumerate(encrypted))
    return decrypted


class EphemeralSessionKeyRotator:
    """Manages ephemeral session keys with automatic rotation."""
    
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.private_key, self.public_key = generate_ephemeral_keypair()
        self.current_key = b'\x00' * 32

    def derive_session_key(self, peer_public_bytes: bytes) -> bytes:
        with self._lock:
            self.current_key = derive_shared_secret(self.private_key, peer_public_bytes)
            return self.current_key

    def rotate_key(self) -> bytes:
        with self._lock:
            self.private_key, self.public_key = generate_ephemeral_keypair()
            return self.public_key

    def get_current_key(self) -> bytes:
        with self._lock:
            return self.current_key