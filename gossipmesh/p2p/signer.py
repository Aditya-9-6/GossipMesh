from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
from typing import Tuple
from gossipmesh.crypto.epoch import get_current_epoch, is_epoch_valid


class EpochP2PSigner:
    """Handles Ed25519 cryptographic key generation and epoch-bound payload signing."""

    def __init__(self, private_key: ed25519.Ed25519PrivateKey = None):
        self.private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

    def get_public_bytes(self) -> bytes:
        return self.public_key.public_bytes_raw()

    def sign_payload(self, payload: bytes, epoch: int) -> Tuple[bytes, int]:
        """Signs a payload combined with an epoch, returning signature and epoch."""
        message = epoch.to_bytes(8, "big", signed=False) + payload
        signature = self.private_key.sign(message)
        return signature, epoch


class EpochP2PVerifier:
    """Verifies epoch-bound Ed25519 signatures against known peer public keys."""

    def __init__(self, epoch_duration_seconds: int = 300, drift_past: int = 1, drift_future: int = 1):
        self.epoch_duration_seconds = epoch_duration_seconds
        self.drift_past = drift_past
        self.drift_future = drift_future

    def verify_payload(self, public_bytes: bytes, payload: bytes, signature: bytes, epoch: int) -> bool:
        """Cryptographically verifies a signed payload and checks its temporal epoch validity."""
        current_epoch = get_current_epoch(self.epoch_duration_seconds)
        if not is_epoch_valid(epoch, current_epoch, self.drift_past, self.drift_future):
            return False

        try:
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)
            message = epoch.to_bytes(8, "big", signed=False) + payload
            pub_key.verify(signature, message)
            return True
        except (InvalidSignature, ValueError):
            return False
