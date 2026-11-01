import os
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from gossipmesh.crypto.ratchet import DoubleRatchetState, RatchetMessage


class SecureMeshTransport:
    def __init__(self, shared_secret: bytes, is_initiator: bool, peer_public_bytes: bytes = None):
        self.ratchet = DoubleRatchetState(shared_secret, is_initiator, peer_public_bytes)
        self.aesgcm = None

    def encrypt(self, plaintext: bytes) -> RatchetMessage:
        msg_key = self.ratchet.ratchet_send()
        nonce = os.urandom(12)
        aesgcm = AESGCM(msg_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        return RatchetMessage(
            ephemeral_public_bytes=self.ratchet.dh_local_pub,
            message_index=self.ratchet.send_n,
            previous_chain_length=self.ratchet.pn,
            ciphertext=ciphertext,
            nonce=nonce,
        )

    def decrypt(self, message: RatchetMessage) -> bytes:
        msg_key = self.ratchet.ratchet_recv(message.ephemeral_public_bytes)
        aesgcm = AESGCM(msg_key)
        return aesgcm.decrypt(message.nonce, message.ciphertext, None)
