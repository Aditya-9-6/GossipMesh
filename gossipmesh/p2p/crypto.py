import os
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization

class EphemeralSessionKeyRotator:
    """Manages ephemeral Curve25519 keys and derives session keys for transport."""
    def __init__(self) -> None:
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.current_key = AESGCM.generate_key(bit_length=256)
        self.session_key = None

    def get_public_bytes(self) -> bytes:
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    def derive_shared_secret(self, peer_public_bytes: bytes) -> bytes:
        peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        shared_secret = self.private_key.exchange(peer_pub)
        self.current_key = shared_secret[:32]
        self.session_key = self.current_key
        return self.current_key

    def rotate(self) -> Tuple[bytes, bytes]:
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.current_key = AESGCM.generate_key(bit_length=256)
        self.session_key = None
        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return self.current_key, pub_bytes

    def rotate_key(self) -> bytes:
        key, _ = self.rotate()
        return key


def encrypt_payload(key: bytes, plaintext: bytes) -> bytes:
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt_payload(key: bytes, ciphertext: bytes) -> bytes:
    aesgcm = AESGCM(key)
    nonce = ciphertext[:12]
    actual_ciphertext = ciphertext[12:]
    return aesgcm.decrypt(nonce, actual_ciphertext, None)
