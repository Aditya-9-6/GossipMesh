import hashlib
import time
from typing import Tuple


def calculate_pow_hash(public_key: str, nonce: int) -> str:
    """Calculates SHA-256 hash of public key concatenated with nonce."""
    data = f"{public_key}:{nonce}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def verify_pow(public_key: str, nonce: int, difficulty: int) -> bool:
    """Verifies if the PoW hash meets the target difficulty (leading zeros)."""
    target_prefix = "0" * difficulty
    h = calculate_pow_hash(public_key, nonce)
    return h.startswith(target_prefix)


def mine_pow(public_key: str, difficulty: int, max_iterations: int = 10000000) -> Tuple[int, str]:
    """Mines a nonce such that the SHA-256 hash meets the target difficulty."""
    target_prefix = "0" * difficulty
    for nonce in range(max_iterations):
        h = calculate_pow_hash(public_key, nonce)
        if h.startswith(target_prefix):
            return nonce, h
    raise ValueError(f"Failed to mine PoW with difficulty {difficulty} within {max_iterations} iterations")
