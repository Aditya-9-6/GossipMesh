import pytest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os


@pytest.fixture(scope="session", autouse=True)
def setup_enterprise_keys():
    """Ensure a matching test private key exists for the enterprise tests."""
    priv_path = Path("enterprise/test_private_key.pem")
    pub_path = Path("enterprise/public_key.pem")

    # Generate new pair always for tests to avoid state issues unless they match
    generate_new = True
    if priv_path.exists() and pub_path.exists():
        try:
            priv_key = serialization.load_pem_private_key(priv_path.read_bytes(), password=None)
            pub_key = serialization.load_pem_public_key(pub_path.read_bytes())
            if priv_key.public_key().public_numbers() == pub_key.public_numbers():
                generate_new = False
        except Exception:
            pass

    if generate_new:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        priv_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        priv_path.parent.mkdir(parents=True, exist_ok=True)
        priv_path.write_bytes(priv_pem)

        pub_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        pub_path.parent.mkdir(parents=True, exist_ok=True)
        pub_path.write_bytes(pub_pem)
