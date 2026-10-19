import pytest
import time
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import jwt


@pytest.fixture(scope="session")
def rsa_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture(scope="session")
def private_key(rsa_key_pair):
    return rsa_key_pair[0]


@pytest.fixture(scope="session")
def public_key(rsa_key_pair):
    return rsa_key_pair[1]


@pytest.fixture(scope="session")
def public_key_pem(public_key):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()


@pytest.fixture(autouse=True, scope="session")
def set_env_public_key(public_key_pem):
    import os

    os.environ["GOSSIMESH_TEST_PUBLIC_KEY_PEM"] = public_key_pem


@pytest.fixture(scope="session")
def valid_license_token(private_key):
    now = int(time.time())
    payload = {
        "iss": "GossipMesh Enterprise Licensing Authority",
        "sub": "enterprise-customer-xyz",
        "iat": now - 3600,
        "exp": now + 86400,
        "bundle_ids": ["b04"],
        "tier": "Enterprise Air-Gapped",
        "task_model_map": {},
        "pricing_usd": 50000,
        "offline_air_gapped": True,
        "version": "1.0",
    }
    return jwt.encode(payload, private_key, algorithm="RS256")
