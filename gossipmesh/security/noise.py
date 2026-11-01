"""
Ephemeral Key Exchange with Noise Protocol XX Handshake Pattern.

Provides mutual authentication, identity hiding, and forward-secret session key derivation
using X25519 (ECDH), ChaCha20Poly1305 (AEAD), and BLAKE2s (Hashing/KDF) per the Noise_XX spec.
"""

from __future__ import annotations

import os
import logging
from typing import Tuple, Optional, Dict, Any

from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

logger = logging.getLogger(__name__)


class NoiseXXState:
    """
    Manages the state and cryptographic operations for the Noise_XX handshake pattern.

    Pattern details:
      - IK (Initiator static key): None (transmitted in handshake)
      - RK (Responder static key): Known or authenticated via payload/trust store
      - Message 1: e -> Initiator ephemeral
      - Message 2: e, ee, s, es -> Responder ephemeral, static, and auth
      - Message 3: s, se -> Initiator static and auth
    """

    def __init__(self, is_initiator: bool, static_private_key: Optional[x25519.X25519PrivateKey] = None):
        self.is_initiator = is_initiator
        self.protocol_name = b"Noise_XX_25519_ChaChaPoly_BLAKE2s"

        # Keys
        self.s_priv = static_private_key or x25519.X25519PrivateKey.generate()
        self.s_pub = self.s_priv.public_key()

        self.e_priv: Optional[x25519.X25519PrivateKey] = None
        self.e_pub: Optional[x25519.X25519PublicKey] = None

        self.remote_s_pub: Optional[x25519.X25519PublicKey] = None
        self.remote_e_pub: Optional[x25519.X25519PublicKey] = None

        # Cryptographic state
        self.h: bytes = b""
        self.ck: bytes = b""
        self.k: Optional[bytes] = None
        self.nonce: int = 0

        self._initialize_handshake()

    def _initialize_handshake(self) -> None:
        # Initialize h and ck with protocol name
        if len(self.protocol_name) <= 32:
            self.h = self.protocol_name.ljust(32, b"\x00")
        else:
            digest = hashes.Hash(hashes.BLAKE2s(32))
            digest.update(self.protocol_name)
            self.h = digest.finalize()
        self.ck = self.h

    def _mix_key(self, ikm: bytes) -> None:
        # HKDF-derived chain key and cipher key
        hkdf = HKDF(
            algorithm=hashes.BLAKE2s(32),
            length=64,
            salt=self.ck,
            info=b"Noise_XX_KDF",
        )
        derived = hkdf.derive(ikm)
        self.ck = derived[:32]
        self.k = derived[32:]
        self.nonce = 0

    def _mix_hash(self, data: bytes) -> None:
        digest = hashes.Hash(hashes.BLAKE2s(32))
        digest.update(self.h)
        digest.update(data)
        self.h = digest.finalize()

    def _encrypt_and_hash(self, plaintext: bytes) -> bytes:
        if self.k is None:
            self._mix_hash(plaintext)
            return plaintext

        cipher = ChaCha20Poly1305(self.k)
        # 12-byte nonce: 4 zero bytes + 8-byte big endian counter
        nonce_bytes = b"\x00" * 4 + self.nonce.to_bytes(8, "big")
        self.nonce += 1
        ciphertext = cipher.encrypt(nonce_bytes, plaintext, self.h)
        self._mix_hash(ciphertext)
        return ciphertext

    def _decrypt_and_hash(self, ciphertext: bytes) -> bytes:
        if self.k is None:
            self._mix_hash(ciphertext)
            return ciphertext

        cipher = ChaCha20Poly1305(self.k)
        nonce_bytes = b"\x00" * 4 + self.nonce.to_bytes(8, "big")
        self.nonce += 1
        plaintext = cipher.decrypt(nonce_bytes, ciphertext, self.h)
        self._mix_hash(ciphertext)
        return plaintext

    def write_message_1(self, payload: bytes = b"") -> bytes:
        """
        Initiator -> Responder: e
        """
        if not self.is_initiator:
            raise ValueError("Only initiator can write message 1")

        self.e_priv = x25519.X25519PrivateKey.generate()
        self.e_pub = self.e_priv.public_key()

        e_pub_bytes = self.e_pub.public_bytes_raw()
        self._mix_hash(e_pub_bytes)

        encrypted_payload = self._encrypt_and_hash(payload)
        return e_pub_bytes + encrypted_payload

    def read_message_1(self, message: bytes) -> bytes:
        """
        Responder reads message 1: e
        """
        if self.is_initiator:
            raise ValueError("Only responder can read message 1")

        e_pub_bytes = message[:32]
        encrypted_payload = message[32:]

        self.remote_e_pub = x25519.X25519PublicKey.from_public_bytes(e_pub_bytes)
        self._mix_hash(e_pub_bytes)

        return self._decrypt_and_hash(encrypted_payload)

    def write_message_2(self, payload: bytes = b"") -> bytes:
        """
        Responder -> Initiator: e, ee, s, es
        """
        if self.is_initiator:
            raise ValueError("Only responder can write message 2")

        self.e_priv = x25519.X25519PrivateKey.generate()
        self.e_pub = self.e_priv.public_key()
        e_pub_bytes = self.e_pub.public_bytes_raw()

        self._mix_hash(e_pub_bytes)

        # ee = e (responder) * e (initiator)
        ee = self.e_priv.exchange(self.remote_e_pub)
        self._mix_key(ee)

        # Encrypt static key s
        s_pub_bytes = self.s_pub.public_bytes_raw()
        encrypted_s = self._encrypt_and_hash(s_pub_bytes)

        # es = s (responder) * e (initiator)
        es = self.s_priv.exchange(self.remote_e_pub)
        self._mix_key(es)

        encrypted_payload = self._encrypt_and_hash(payload)
        return e_pub_bytes + encrypted_s + encrypted_payload

    def read_message_2(self, message: bytes) -> bytes:
        """
        Initiator reads message 2: e, ee, s, es
        """
        if not self.is_initiator:
            raise ValueError("Only initiator can read message 2")

        e_pub_bytes = message[:32]
        encrypted_s = message[32 : 72 + 16]  # 32 + 32 (pub) + 16 (tag)
        encrypted_payload = message[72 + 16 :]

        self.remote_e_pub = x25519.X25519PublicKey.from_public_bytes(e_pub_bytes)
        self._mix_hash(e_pub_bytes)

        ee = self.e_priv.exchange(self.remote_e_pub)
        self._mix_key(ee)

        s_bytes = self._decrypt_and_hash(encrypted_s)
        self.remote_s_pub = x25519.X25519PublicKey.from_public_bytes(s_bytes)

        es = self.e_priv.exchange(self.remote_s_pub)
        self._mix_key(es)

        return self._decrypt_and_hash(encrypted_payload)

    def write_message_3(self, payload: bytes = b"") -> bytes:
        """
        Initiator -> Responder: s, se
        """
        if not self.is_initiator:
            raise ValueError("Only initiator can write message 3")

        s_pub_bytes = self.s_pub.public_bytes_raw()
        encrypted_s = self._encrypt_and_hash(s_pub_bytes)

        se = self.s_priv.exchange(self.remote_e_pub)
        self._mix_key(se)

        encrypted_payload = self._encrypt_and_hash(payload)
        return encrypted_s + encrypted_payload

    def read_message_3(self, message: bytes) -> bytes:
        """
        Responder reads message 3: s, se
        """
        if self.is_initiator:
            raise ValueError("Only responder can read message 3")

        encrypted_s = message[: 32 + 16]
        encrypted_payload = message[32 + 16 :]

        s_bytes = self._decrypt_and_hash(encrypted_s)
        self.remote_s_pub = x25519.X25519PublicKey.from_public_bytes(s_bytes)

        se = self.e_priv.exchange(self.remote_s_pub)
        self._mix_key(se)

        return self._decrypt_and_hash(encrypted_payload)

    def finalize(self) -> Tuple[bytes, bytes]:
        """
        Derives final transport encryption keys (initiator_send_key, responder_send_key).
        """
        hkdf = HKDF(
            algorithm=hashes.BLAKE2s(32),
            length=64,
            salt=self.ck,
            info=b"Noise_XX_Transport",
        )
        derived = hkdf.derive(b"")
        if self.is_initiator:
            return derived[:32], derived[32:]
        else:
            return derived[32:], derived[:32]
