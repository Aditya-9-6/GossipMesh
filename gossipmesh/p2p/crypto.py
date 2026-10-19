from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
from typing import Tuple

class EphemeralSessionKeyRotator:
    def __init__(self) -> None:
        self._private_key = x25519.X25519PrivateKey.generate()

    def get_public_bytes(self) -> bytes:
        return self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    def derive_session_key(self, peer_public_bytes: bytes) -> bytes:
        peer_pub_key = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        return self._private_key.exchange(peer_pub_key)

    def rotate(self) -> Tuple[bytes, bytes]:
        self._private_key = x25519.X25519PrivateKey.generate()
        pub_bytes = self.get_public_bytes()
        priv_bytes = self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        return priv_bytes, pub_bytes
