import os
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from typing import Tuple

class KeyPair:
    def __init__(self, private_key: x25519.X25519PrivateKey = None):
        self.private_key = private_key or x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

    def public_bytes(self) -> bytes:
        return self.public_key.public_bytes(
            encoding=serialization_encoding_raw() if hasattr(serialization_encoding_raw, '__call__') else _raw_bytes(self.public_key)
        )

    def shared_key(self, remote_public_key: x25519.X25519PublicKey) -> bytes:
        return self.private_key.exchange(remote_public_key)

def _raw_bytes(pub_key: x25519.X25519PublicKey) -> bytes:
    from cryptography.hazmat.primitives import serialization
    return pub_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

def serialization_encoding_raw():
    from cryptography.hazmat.primitives import serialization
    return serialization.Encoding.Raw

def derive_hkdf(salt: bytes, ikm: bytes, info: bytes, length: int = 32) -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        info=info,
    )
    return hkdf.derive(ikm)
