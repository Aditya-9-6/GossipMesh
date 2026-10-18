import os
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from gossipmesh.crypto.keys import KeyPair, derive_hkdf

class DoubleRatchetSession:
    def __init__(self, dh_local: KeyPair, dh_remote_pub: x25519.X25519PublicKey, root_key: bytes):
        self.dh_local = dh_local
        self.dh_remote_pub = dh_remote_pub
        self.root_key = root_key
        self.send_chain_key = None
        self.recv_chain_key = None
        self.message_number_send = 0
        self.message_number_recv = 0

    @classmethod
    def initiate(cls, local_keypair: KeyPair, remote_public_key: x25519.X25519PublicKey, shared_secret: bytes) -> 'DoubleRatchetSession':
        session = cls(local_keypair, remote_public_key, shared_secret)
        session.send_chain_key = derive_hkdf(b"gossipmesh-ratchet-salt", shared_secret, b"send-chain", 32)
        session.recv_chain_key = derive_hkdf(b"gossipmesh-ratchet-salt", shared_secret, b"recv-chain", 32)
        return session

    def _ratchet_step(self, remote_pub: x25519.X25519PublicKey) -> None:
        self.dh_remote_pub = remote_pub
        shared = self.dh_local.shared_key(remote_pub)
        derived = derive_hkdf(self.root_key, shared, b"root-ratchet", 64)
        self.root_key = derived[:32]
        self.recv_chain_key = derived[32:]
        self.dh_local = KeyPair()
        new_shared = self.dh_local.shared_key(remote_pub)
        derived_send = derive_hkdf(self.root_key, new_shared, b"root-ratchet-send", 64)
        self.root_key = derived_send[:32]
        self.send_chain_key = derived_send[32:]
