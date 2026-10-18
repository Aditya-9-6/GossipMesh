import json
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
from gossipmesh.crypto.epoch import get_current_epoch, is_epoch_valid

class PayloadSigner:
    """Ed25519 cryptographic signer for gossip payloads bound to temporal epochs."""
    def __init__(self, private_key: Optional[ed25519.Ed25519PrivateKey] = None):
        self.private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

    def sign_payload(self, payload: Dict[str, Any], epoch: Optional[int] = None) -> Dict[str, Any]:
        target_epoch = epoch if epoch is not None else get_current_epoch()
        envelope = {
            "payload": payload,
            "epoch": target_epoch
        }
        canonical_bytes = json.dumps(envelope["payload"], sort_keys=True, separators=(",", ":")).encode("utf-8")
        message_bytes = f"{target_epoch}:".encode("utf-8") + canonical_bytes
        signature = self.private_key.sign(message_bytes)
        envelope["signature"] = signature.hex()
        return envelope

class PayloadVerifier:
    """Ed25519 cryptographic verifier for gossip payloads bound to temporal epochs."""
    def __init__(self, public_key: ed25519.Ed25519PublicKey):
        self.public_key = public_key

    def verify_envelope(self, envelope: Dict[str, Any], tolerance_epochs: int = 1) -> bool:
        try:
            epoch = envelope.get("epoch")
            payload = envelope.get("payload")
            signature_hex = envelope.get("signature")

            if epoch is None or payload is None or signature_hex is None:
                return False

            if not is_epoch_valid(epoch, tolerance_epochs=tolerance_epochs):
                return False

            canonical_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            message_bytes = f"{epoch}:".encode("utf-8") + canonical_bytes
            signature = bytes.fromhex(signature_hex)

            self.public_key.verify(signature, message_bytes)
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False
