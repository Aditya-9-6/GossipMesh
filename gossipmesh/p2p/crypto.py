class EphemeralSessionKeyRotator:
    """Manages ephemeral session keys for secure P2P channels."""
    def __init__(self) -> None:
        self._public_bytes = b"mock_ephemeral_pub_key_32_bytes"

    def get_public_bytes(self) -> bytes:
        return self._public_bytes

def encrypt_payload(plaintext: bytes, key: bytes) -> bytes:
    return b"enc_" + plaintext

def decrypt_payload(ciphertext: bytes, key: bytes) -> bytes:
    if ciphertext.startswith(b"enc_"):
        return ciphertext[4:]
    return ciphertext
