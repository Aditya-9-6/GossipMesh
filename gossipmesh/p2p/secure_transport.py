from typing import Tuple, Optional
from gossipmesh.crypto.keys import KeyPair
from gossipmesh.crypto.ratchet import DoubleRatchetSession

class SecureP2PTransport:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.keypair = KeyPair()
        self.sessions = {} # peer_id -> DoubleRatchetSession

    def establish_session(self, peer_id: str, peer_public_bytes: bytes, shared_secret: bytes) -> DoubleRatchetSession:
        from cryptography.hazmat.primitives.asymmetric import x25519
        from gossipmesh.crypto.keys import serialization_encoding_raw
        peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
        session = DoubleRatchetSession.initiate(self.keypair, peer_pub, shared_secret)
        self.sessions[peer_id] = session
        return session

    def send_secure_message(self, peer_id: str, plaintext: bytes, associated_data: bytes = b"") -> Tuple[bytes, bytes, int]:
        session = self.sessions.get(peer_id)
        if not session:
            raise KeyError(f"No active secure session with peer {peer_id}")
        return session.encrypt(plaintext, associated_data)

    def receive_secure_message(self, peer_id: str, peer_public_bytes: bytes, payload: bytes, seq: int, associated_data: bytes = b"") -> bytes:
        session = self.sessions.get(peer_id)
        if not session:
            raise KeyError(f"No active secure session with peer {peer_id}")
        return session.decrypt(peer_public_bytes, payload, seq, associated_data)
