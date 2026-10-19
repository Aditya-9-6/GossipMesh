import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StateCheckpoint:
    epoch: int
    node_id: str
    state_root: str
    timestamp: float = field(default_factory=time.time)
    signature: Optional[str] = None

    def compute_hash(self) -> str:
        payload = {
            "epoch": self.epoch,
            "node_id": self.node_id,
            "state_root": self.state_root,
            "timestamp": self.timestamp,
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def sign(self, secret_key: str) -> str:
        msg = self.compute_hash().encode("utf-8")
        key = secret_key.encode("utf-8")
        self.signature = hmac.new(key, msg, hashlib.sha256).hexdigest()
        return self.signature

    def verify_signature(self, public_key_or_secret: str) -> bool:
        if not self.signature:
            return False
        msg = self.compute_hash().encode("utf-8")
        key = public_key_or_secret.encode("utf-8")
        expected = hmac.new(key, msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.signature, expected)


def hmac_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
