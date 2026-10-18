import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set

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
            "timestamp": self.timestamp
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def sign(self, secret_key: str) -> str:
        hasher = hashlib.sha256()
        hasher.update(self.compute_hash().encode("utf-8"))
        hasher.update(secret_key.encode("utf-8"))
        self.signature = hasher.hexdigest()
        return self.signature

    def verify_signature(self, public_key_or_secret: str) -> bool:
        if not self.signature:
            return False
        hasher = hashlib.sha256()
        hasher.update(self.compute_hash().encode("utf-8"))
        hasher.update(public_key_or_secret.encode("utf-8"))
        expected = hasher.hexdigest()
        return hmac_compare(self.signature, expected)

def hmac_compare(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0
