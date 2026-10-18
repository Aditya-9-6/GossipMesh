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
        derived_recv_full = derive_hkdf(self.root_key, shared, b"root-ratchet", 64)
        self.root_key = derived_recv_full[:32]
        self.recv_chain_key = derived_recv_full[32:]

        self.dh_local = KeyPair()
        new_shared = self.dh_local.shared_key(remote_pub)
        derived_send_full = derive_hkdf(self.root_key, new_shared, b"root-ratchet-send", 64)
        self.root_key = derived_send_full[:32]
        self.send_chain_key = derived_send_full[32:]
        self.message_number_send = 0
        self.message_number_recv = 0

    def encrypt(self, plaintext: bytes, associated_data: bytes = b"") -> Tuple[bytes, bytes, int]:
        if not self.send_chain_key:
            raise ValueError("Send chain key not initialized")
        
        mk = derive_hkdf(self.send_chain_key, b"message-key", b"", 32)
        self.send_chain_key = derive_hkdf(self.send_chain_key, b"next-chain-key", b"", 32)
        
        nonce = os.urandom(12)
        cipher = ChaCha20Poly1305(mk)
        ciphertext = cipher.encrypt(nonce, plaintext, associated_data)
        
        pub_bytes = self.dh_local.public_bytes()
        seq = self.message_number_send
        self.message_number_send += 1
        
        payload = nonce + ciphertext
        return pub_bytes, payload, seq

    def decrypt(self, remote_pub_bytes: bytes, payload: bytes, seq: int, associated_data: bytes = b"") -> bytes:
        from cryptography.hazmat.primitives.asymmetric import x25519
        remote_pub = x25519.X25519PublicKey.from_public_bytes(remote_pub_bytes)
        
        if remote_pub.public_bytes(serialization_encoding_raw() if hasattr(serialization_encoding_raw(), '__call__') else _raw_bytes_pub(remote_pub)) != self.dh_remote_pub.public_bytes(serialization_encoding_raw() if hasattr(serialization_encoding_raw(), '__call__') else _raw_bytes_pub(self.dh_remote_pub)):
            self._ratchet_step(remote_pub)
            
        mk = derive_hkdf(self.recv_chain_key, b"message-key", b"", 32)
        self.recv_chain_key = derive_hkdf(self.recv_chain_key, b"next-chain-key", b"", 32)
        
        nonce = payload[:12]
        ciphertext = payload[12:]
        
        cipher = ChaCha20Poly1305(mk)
        return cipher.decrypt(nonce, ciphertext, associated_data)

def _raw_bytes_pub(pub_key: x25519.X25519PublicKey) -> bytes:
    from cryptography.hazmat.primitives import serialization
    return pub_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
