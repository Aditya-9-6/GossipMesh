from typing import Optional
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os


class EphemeralSessionKeyRotator:
    """Manages ephemeral session keys with automatic rotation."""

    def __init__(self) -> None:
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self._current_key: bytes = AESGCM.generate_key(bit_length=128)

    def initialize(self, peer_public_bytes: bytes) -> None:
        peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        shared_key = self.private_key.exchange(peer_pub)
        self._current_key = AESGCM(shared_key)

    @property
    def current_key(self) -> bytes:
        return self._current_key

    def rotate(self) -> bytes:
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self._current_key = AESGCM.generate_key(bit_length=128)
        return self.public_key.public_bytes_raw()


def encrypt_payload(plaintext: bytes, key: bytes) -> bytes:
    aesgcm = AESGCM(key if isinstance(key, bytes) else AESGCM.generate_key(bit_length=128))
    nonce = os.urandom(12)
    return nonce + aesgcm.encrypt(nonce, plaintext, None)


def decrypt_payload(ciphertext: bytes, key: bytes) -> bytes:
    aesgcm = AESGCM(key if isinstance(key, bytes) else AESGCM.generate_key(bit_length=128))
    nonce = ciphertext[:12]
    return aesgcm.decrypt(nonce, ciphertext[12:], None)
