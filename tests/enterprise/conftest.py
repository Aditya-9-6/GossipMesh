import os
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def _ensure_private_key():
    """Ensure that test_private_key.pem exists for enterprise licensing tests."""
    ensure_test_private_key()
    key_path = Path("enterprise/test_private_key.pem")
    if not key_path.is_file():
        key_path.parent.mkdir(parents=True, exist_ok=True)
        # Generate a test RSA private key if missing
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path.write_bytes(pem)

    os.environ.setdefault("LICENSE_PRIVATE_KEY_PATH", str(key_path.resolve()))
    yield


def ensure_test_private_key():
    """Helper to ensure test private key exists."""
    key_path = Path("enterprise/test_private_key.pem")
    if not key_path.is_file():
        key_path.parent.mkdir(parents=True, exist_ok=True)
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path.write_bytes(pem)
