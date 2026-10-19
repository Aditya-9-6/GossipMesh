import os
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


class EphemeralSessionKeyRotator:
    """Manages ephemeral X25519 key exchanges and session key derivation."""

    def __init__(self) -> None:
        self._private_key = x25519.X25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        self._shared_key: bytes = b""
        self.session_key: bytes = b""
        self.current_key: bytes = b""

    def get_public_bytes(self) -> bytes:
        return self._public_key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)

    def derive_shared_secret(self, peer_public_bytes: bytes) -> bytes:
        peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        self._shared_key = self._private_key.exchange(peer_pub)
        derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"gossipmesh-session-key").derive(
            self._shared_key
        )
        self.session_key = derived
        self.current_key = derived
        return derived

    def rotate(self) -> Tuple[bytes, bytes]:
        """Rotates the ephemeral keypair and returns (private_bytes, public_bytes)."""
        self._private_key = x25519.X25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        self.session_key = b""
        self.current_key = b""
        priv_bytes = self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return priv_bytes, self.get_public_bytes()


def encrypt_payload(key: bytes, plaintext: bytes) -> bytes:
    if not key:
        return plaintext
    cipher = ChaCha20Poly1305(key)
    nonce = os.urandom(12)
    return nonce + cipher.encrypt(nonce, plaintext, None)


def decrypt_payload(key: bytes, ciphertext: bytes) -> bytes:
    if not key or len(ciphertext) < 12:
        return ciphertext
    cipher = ChaCha20Poly1305(key)
    nonce = ciphertext[:12]
    ct = ciphertext[12:]
    return cipher.decrypt(nonce, ct, None)
