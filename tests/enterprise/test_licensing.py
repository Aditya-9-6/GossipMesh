import pytest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from scripts.issue_license import load_private_key
import os


@pytest.fixture
def private_key(tmp_path):
    """Load or generate test private key."""
    key_path = tmp_path / "test_private_key.pem"
    if not key_path.exists():
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
    return load_private_key(str(key_path))
