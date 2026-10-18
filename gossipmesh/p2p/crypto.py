import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization

class EphemeralSessionKeyRotator:
    def __init__(self):
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.current_key: bytes = AESGCM.generate_key(bit_length=128)

    def get_public_bytes(self) -> bytes:
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    def derive_shared_secret(self, peer_public_bytes: bytes) -> bytes:
        peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        shared = self.private_key.exchange(peer_pub)
        self.current_key = hashlib.sha256(shared).digest()[:16]
        return self.current_key

    def derive_session_key(self, peer_public_bytes: bytes) -> bytes:
        return self.derive_shared_secret(peer_public_bytes)

    def rotate(self) -> tuple[bytes, bytes]:
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.current_key = AESGCM.generate_key(bit_length=128)
        return self.get_public_bytes(), self.current_key

def encrypt_payload(key: bytes, plaintext: bytes, associated_data: bytes = b"") -> bytes:
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
    return nonce + ciphertext

def decrypt_payload(key: bytes, ciphertext: bytes, associated_data: bytes = b"") -> bytes:
    aesgcm = AESGCM(key)
    nonce = ciphertext[:12]
    ct = ciphertext[12:]
    return aesgcm.decrypt(nonce, ct, associated_data)
