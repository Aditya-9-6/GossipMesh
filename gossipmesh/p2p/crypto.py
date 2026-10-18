from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Tuple

class EphemeralSessionKeyRotator:
    def __init__(self):
        self._private_key = x25519.X25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        self.session_key = b''
        self.current_key = b''

    def get_public_bytes(self) -> bytes:
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    def derive_shared_secret(self, peer_public_bytes: bytes) -> bytes:
        peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        shared_secret = self._private_key.exchange(peer_pub)
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'gossipmesh-handshake'
        )
        self.session_key = hkdf.derive(shared_secret)
        self.current_key = self.session_key
        return self.session_key

    def rotate(self) -> Tuple[bytes, bytes]:
        """Rotates the ephemeral keypair and returns (private_bytes, public_bytes)."""
        self._private_key = x25519.X25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()
        self.session_key = b''
        self.current_key = b''
        priv_bytes = self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        pub_bytes = self.get_public_bytes()
        return priv_bytes, pub_bytes

def encrypt_payload(key: bytes, plaintext: bytes) -> bytes:
    if not key:
        key = b'\x00' * 32
    aesgcm = AESGCM(key)
    nonce = b'\x00' * 12
    return aesgcm.encrypt(nonce, plaintext, None)

def decrypt_payload(key: bytes, ciphertext: bytes) -> bytes:
    if not key:
        key = b'\x00' * 32
    aesgcm = AESGCM(key)
    nonce = b'\x00' * 12
    return aesgcm.decrypt(nonce, ciphertext, None)
