import os
import hmac
import hashlib
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import serialization

CIPHER_KEY_LEN = 32


class NoiseHandshakeState:
    def __init__(self, is_initiator: bool, s_priv: x25519.X25519PrivateKey):
        self.is_initiator = is_initiator
        self.s_priv = s_priv
        self.s_pub = s_priv.public_key()
        self.e_priv = x25519.X25519PrivateKey.generate()
        self.e_pub = self.e_priv.public_key()
        
        self.remote_s_pub = None
        self.remote_e_pub = None
        
        self.h = hashlib.sha256(b"Noise_XX_25519_ChaChaPoly_SHA256").digest()
        self.ck = self.h
        self.key = None
        self.nonce = 0

    def _mix_hash(self, data: bytes):
        self.h = hashlib.sha256(self.h + data).digest()

    def _hkdf(self, ikm: bytes) -> Tuple[bytes, bytes]:
        hmac_key = hmac.new(self.ck, ikm, hashlib.sha256).digest()
        output1 = hmac.new(hmac_key, b"\x01", hashlib.sha256).digest()
        output2 = hmac.new(hmac_key, output1 + b"\x02", hashlib.sha256).digest()
        return output1, output2

    def _mix_key(self, ikm: bytes):
        self.ck, self.key = self._hkdf(ikm)
        self.nonce = 0

    def encrypt_and_hash(self, plaintext: bytes) -> bytes:
        if self.key is None:
            self._mix_hash(plaintext)
            return plaintext
        cipher = ChaCha20Poly1305(self.key)
        ciphertext = cipher.encrypt(self.nonce.to_bytes(12, "big"), plaintext, self.h)
        self.nonce += 1
        self._mix_hash(ciphertext)
        return ciphertext

    def decrypt_and_hash(self, ciphertext: bytes) -> bytes:
        if self.key is None:
            self._mix_hash(ciphertext)
            return ciphertext
        cipher = ChaCha20Poly1305(self.key)
        plaintext = cipher.decrypt(self.nonce.to_bytes(12, "big"), ciphertext, self.h)
        self.nonce += 1
        self._mix_hash(ciphertext)
        return plaintext

    def write_message_1(self) -> bytes:
        assert self.is_initiator
        e_bytes = self.e_pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self._mix_hash(e_bytes)
        return e_bytes

    def read_message_1(self, message: bytes):
        assert not self.is_initiator
        self.remote_e_pub = x25519.X25519PublicKey.from_public_bytes(message)
        self._mix_hash(message)

    def write_message_2(self) -> bytes:
        assert not self.is_initiator
        e_bytes = self.e_pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self._mix_hash(e_bytes)
        self._mix_key(self.e_priv.exchange(self.remote_e_pub))
        
        s_bytes = self.s_pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        enc_s = self.encrypt_and_hash(s_bytes)
        self._mix_key(self.e_priv.exchange(self.remote_s_pub) if self.remote_s_pub else b"\x00" * 32)
        
        payload = b""
        enc_payload = self.encrypt_and_hash(payload)
        return e_bytes + enc_s + enc_payload

    def read_message_2(self, message: bytes):
        assert self.is_initiator
        e_bytes = message[:32]
        self.remote_e_pub = x25519.X25519PublicKey.from_public_bytes(e_bytes)
        self._mix_hash(e_bytes)
        self._mix_key(self.e_priv.exchange(self.remote_e_pub))
        
        enc_s = message[32:32 + 32 + 16]
        s_bytes = self.decrypt_and_hash(enc_s)
        self.remote_s_pub = x25519.X25519PublicKey.from_public_bytes(s_bytes)
        self._mix_key(self.e_priv.exchange(self.remote_s_pub) if self.remote_s_pub else b"\x00" * 32)
        
        enc_payload = message[32 + 32 + 16:]
        self.decrypt_and_hash(enc_payload)

    def write_message_3(self) -> bytes:
        assert self.is_initiator
        s_bytes = self.s_pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        enc_s = self.encrypt_and_hash(s_bytes)
        self._mix_key(self.s_priv.exchange(self.remote_e_pub) if self.remote_e_pub else b"\x00" * 32)
        
        payload = b""
        enc_payload = self.encrypt_and_hash(payload)
        return enc_s + enc_payload

    def read_message_3(self, message: bytes):
        assert not self.is_initiator
        enc_s = message[:32 + 16]
        s_bytes = self.decrypt_and_hash(enc_s)
        self.remote_s_pub = x25519.X25519PublicKey.from_public_bytes(s_bytes)
        self._mix_key(self.s_priv.exchange(self.remote_e_pub) if self.remote_e_pub else b"\x00" * 32)
        
        enc_payload = message[32 + 16:]
        self.decrypt_and_hash(enc_payload)
