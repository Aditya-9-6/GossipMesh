import pytest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


@pytest.fixture(autouse=True)
def ensure_test_private_key(tmp_path, monkeypatch):
    enterprise_dir = Path(__file__).resolve().parent.parent.parent / "enterprise"
    enterprise_dir.mkdir(parents=True, exist_ok=True)
    key_path = enterprise_dir / "test_private_key.pem"
    if not key_path.exists():
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        key_path.write_bytes(pem)
