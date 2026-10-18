import os
import threading
from typing import Tuple, Optional
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class EphemeralSessionKeyRotator:
    """Manages ephemeral X25519 key pairs and derives session keys using HKDF-SHA256."""

    def __init__(self) -> None:
        self._private_key = x25519.X25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        self._session_key: Optional[bytes] = None
        self._lock = threading.Lock()

    @property
    def session_key(self) -> Optional[bytes]:
        with self._lock:
            return self._session_key

    def get_public_bytes(self) -> bytes:
        return self._public_key.public_bytes(
            encoding=hashes.serialization.Encoding.Raw,
            format=hashes.serialization.PublicFormat.Raw
        )

    def derive_session_key(self, peer_public_bytes: bytes) -> bytes:
        peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        shared_key = self._private_key.exchange(peer_pub)
        derived = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"gossipmesh-p2p-salt",
            info=b"gossipmesh-session-key"
        ).derive(shared_key)
        with self._lock:
            self._session_key = derived
        return derived

    def rotate(self) -> Tuple[bytes, bytes]:
        with self._lock:
            self._private_key = x25519.X25519PrivateKey.generate()
            self._public_key = self._private_key.public_key()
            self._session_key = None
            return self.get_public_bytes(), self.get_public_bytes()

    def rotate_key(self) -> bytes:
        self.rotate()
        return self.get_public_bytes()

    def get_current_key(self) -> bytes:
        with self._lock:
            if self._session_key is None:
                raise ValueError("Session key has not been derived yet.")
            return self._session_key


def encrypt_payload(plaintext: bytes, session_key: bytes) -> bytes:
    aesgcm = AESGCM(session_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt_payload(ciphertext: bytes, session_key: bytes) -> bytes:
    if len(ciphertext) < 12:
        raise ValueError("Ciphertext too short.")
    aesgcm = AESGCM(session_key)
    nonce = ciphertext[:12]
    actual_ct = ciphertext[12:]
    return aesgcm.decrypt(nonce, actual_ct, None)
