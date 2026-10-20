import os
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization
from typing import Tuple, Optional


class EphemeralSessionKeyRotator:
    """Handles X25519 Ephemeral Diffie-Hellman key exchange and HKDF key derivation
    for forward-secure session key rotation without dropping active streams."""

    def __init__(self):
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.session_key: Optional[bytes] = None
        self.message_counter: int = 0
        self.last_rotation_time: float = os.times()[4] if hasattr(os, "times") else 0.0

    def get_public_bytes(self) -> bytes:
        return self.public_key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)

    def derive_session_key(self, peer_public_bytes: bytes) -> bytes:
        peer_pub_key = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        shared_secret = self.private_key.exchange(peer_pub_key)

        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"gossipmesh-p2p-salt-v1",
            info=b"session-key-rotation",
        ).derive(shared_secret)

        self.session_key = derived_key
        self.message_counter = 0
        return derived_key

    def rotate(self) -> Tuple["x25519.X25519PrivateKey", bytes]:
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.session_key = None
        self.message_counter = 0
        return self.private_key, self.get_public_bytes()


def encrypt_payload(session_key: bytes, plaintext: bytes) -> bytes:
    aesgcm = AESGCM(session_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt_payload(session_key: bytes, ciphertext_with_nonce: bytes) -> bytes:
    if len(ciphertext_with_nonce) < 12:
        raise ValueError("Ciphertext too short to contain nonce.")
    aesgcm = AESGCM(session_key)
    nonce = ciphertext_with_nonce[:12]
    ciphertext = ciphertext_with_nonce[12:]
    return aesgcm.decrypt(nonce, ciphertext, None)
