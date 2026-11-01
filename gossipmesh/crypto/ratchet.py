from dataclasses import dataclass
from typing import Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import x25519
from gossipmesh.crypto.keys import generate_x25519_keypair, hkdf_derive, x25519_dh


@dataclass
class RatchetMessage:
    ephemeral_public_bytes: bytes
    message_index: int
    previous_chain_length: int
    ciphertext: bytes
    nonce: bytes


class DoubleRatchetState:
    def __init__(self, shared_secret: bytes, is_initiator: bool, peer_public_bytes: Optional[bytes] = None):
        self.dh_local, self.dh_local_pub = generate_x25519_keypair()
        self.dh_remote_pub = peer_public_bytes
        self.root_key = shared_secret
        self.send_chain_key: Optional[bytes] = None
        self.recv_chain_key: Optional[bytes] = None
        self.send_n = 0
        self.recv_n = 0
        self.pn = 0

        if is_initiator and peer_public_bytes:
            dh_out = x25519_dh(self.dh_local, peer_public_bytes)
            derived = hkdf_derive(b"gossipmesh-ratchet-salt", dh_out, b"root-chain-init", 64)
            self.root_key = derived[:32]
            self.send_chain_key = derived[32:]

    def ratchet_send(self) -> bytes:
        if not self.send_chain_key:
            # Initialize send chain
            if self.dh_remote_pub:
                dh_out = x25519_dh(self.dh_local, self.dh_remote_pub)
                derived = hkdf_derive(self.root_key, dh_out, b"gossipmesh-send-step", 64)
                self.root_key = derived[:32]
                self.send_chain_key = derived[32:]
            else:
                self.send_chain_key = hkdf_derive(self.root_key, b"send-fallback", b"chain", 32)

        derived_msg = hkdf_derive(self.send_chain_key, b"msg-key", b"gossipmesh", 64)
        self.send_chain_key = derived_msg[:32]
        message_key = derived_msg[32:]
        self.send_n += 1
        return message_key

    def ratchet_recv(self, peer_ephemeral_pub: bytes) -> bytes:
        if self.dh_remote_pub != peer_ephemeral_pub:
            self.dh_remote_pub = peer_ephemeral_pub
            self.pn = self.send_n
            self.send_n = 0
            self.recv_n = 0
            dh_out = x25519_dh(self.dh_local, peer_ephemeral_pub)
            derived = hkdf_derive(self.root_key, dh_out, b"gossipmesh-recv-step", 64)
            self.root_key = derived[:32]
            self.recv_chain_key = derived[32:]

        derived_msg = hkdf_derive(self.recv_chain_key, b"msg-key", b"gossipmesh", 64)
        self.recv_chain_key = derived_msg[:32]
        message_key = derived_msg[32:]
        self.recv_n += 1
        return message_key
