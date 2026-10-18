import os
import threading
from typing import Tuple

class EphemeralSessionKeyRotator:
    def __init__(self):
        self._lock = threading.Lock()
        self.current_key = os.urandom(32)

    def get_public_bytes(self) -> bytes:
        return self.current_key

    def derive_shared_secret(self, peer_public_bytes: bytes) -> bytes:
        with self._lock:
            # Simulate key derivation/handshake
            self.current_key = bytes(a ^ b for a, b in zip(self.current_key, peer_public_bytes))
            return self.current_key

    def rotate(self) -> bytes:
        with self._lock:
            self.current_key = os.urandom(32)
            return self.current_key

def encrypt_payload(key: bytes, plaintext: bytes) -> bytes:
    return bytes(p ^ key[i % len(key)] for i, p in enumerate(plaintext))

def decrypt_payload(key: bytes, ciphertext: bytes) -> bytes:
    return encrypt_payload(key, ciphertext)
