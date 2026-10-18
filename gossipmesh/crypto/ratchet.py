import os
from typing import Tuple, Optional
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from gossipmesh.crypto.keys import KeyPair, derive_hkdf

class DoubleRatchetSession:
    def __init__(self, dh_local: KeyPair, dh_remote_pub: x25519.X25519PublicKey, root_key: bytes):
        self.dh_local = dh_local
        self.dh_remote_pub = dh_remote_pub
        self.root_key = root_key
        self.send_chain_key: Optional[bytes] = None
        self.recv_chain_key: Optional[bytes] = None
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
        derived_root_recv = derive_hkdf(self.root_key, shared, b"root-ratchet", 64)
        self.root_key = derived_root_recv[:32]
        self.recv_chain_key = derived_root_recv[32:]

        self.dh_local = KeyPair()
        new_shared = self.dh_local.shared_key(remote_pub)
        derived_root_send = derive_hkdf(self.root_key, new_shared, b"root-ratchet-send", 64)
        self.root_key = derived_root_send[:32]
        self.send_chain_key = derived_root_send[32:]

    def encrypt(self, plaintext: bytes) -> bytes:
        if not self.send_chain_key:
            raise ValueError("Send chain key not initialized")
        derived = derive_hkdf(self.send_chain_key, b"", b"message-encryption", 64)
        self.send_chain_key = derived[:32]
        message_key = derived[32:]

        nonce = os.urandom(12)
        cipher = ChaCha20Poly1305(message_key)
        ciphertext = cipher.encrypt(nonce, plaintext, None)

        public_bytes = self.dh_local.public_bytes()
        header_len = len(public_bytes)

        payload = bytearray()
        payload.extend(header_len.to_bytes(2, 'big'))
        payload.extend(public_bytes)
        payload.extend(nonce)
        payload.extend(ciphertext)
        return bytes(payload)

    def decrypt(self, payload: bytes) -> bytes:
        if len(payload) < 2 + 32 + 12:
            raise ValueError("Malformed payload: smaller than minimum header length")
        
        header_len = int.from_bytes(payload[:2], 'big')
        if len(payload) < 2 + header_len + 12:
            raise IndexError("Malformed payload slice length: insufficient bytes for public key and nonce")

        pub_bytes = payload[2:2 + header_len]
        nonce = payload[2 + header_len:2 + header_len + 12]
        ciphertext = payload[2 + header_len + 12:]

        remote_pub = x25519.X25519PublicKey.from_public_bytes(pub_bytes)
        self._ratchet_step(remote_pub)

        if not self.recv_chain_key:
            raise ValueError("Receive chain key not initialized")

        derived = derive_hkdf(self.recv_chain_key, b"", b"message-encryption", 64)
        self.recv_chain_key = derived[:32]
        message_key = derived[32:]

        cipher = ChaCha20Poly1305(message_key)
        return cipher.decrypt(nonce, ciphertext, None)
