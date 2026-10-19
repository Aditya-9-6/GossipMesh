import time
import pytest
import jwt
from pathlib import Path

from enterprise.licensing import (
    verify_license,
    get_license_token,
    load_public_key,
    load_private_key,
    LicenseExpiredError,
    LicenseInvalidError,
    LicenseBundleError,
    LicenseTaskModelError,
)


@pytest.fixture
def rsa_keys(tmp_path):
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )
    public_key = private_key.public_key()

    priv_path = tmp_path / "private.pem"
    pub_path = tmp_path / "public.pem"

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    priv_path.write_bytes(priv_bytes)
    pub_path.write_bytes(pub_bytes)

    return priv_path, pub_path


@pytest.fixture
def private_key(rsa_keys):
    priv_path, _ = rsa_keys
    return load_private_key(priv_path)


@pytest.fixture
def public_key_path(rsa_keys):
    _, pub_path = rsa_keys
    return pub_path


@pytest.fixture
def valid_license_token(private_key):
    now = int(time.time())
    payload = {
        "iss": "GossipMesh Enterprise Licensing Authority",
        "sub": "acme-corp",
        "iat": now - 3600,
        "exp": now + 86400,
        "bundle_ids": ["b01", "b02", "b04"],
        "task_model_map": {},
        "pricing_usd": 50000,
        "offline_air_gapped": True,
        "version": "1.0",
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def test_valid_offline_license_verification(valid_license_token, public_key_path):
    """Ensure a properly signed RSA-4096 license validates offline."""
    payload = verify_license(token=valid_license_token, public_key_path=public_key_path, required_bundle="b04")
    assert payload["sub"] == "acme-corp"
    assert "b04" in payload["bundle_ids"]


def test_expired_license_error(private_key, public_key_path):
    """Ensure expired license raises LicenseExpiredError."""
    now = int(time.time())
    expired_payload = {
        "iss": "GossipMesh Enterprise",
        "sub": "expired-corp",
        "iat": now - 7200,
        "exp": now - 3600,
        "bundle_ids": ["b04"],
        "tier": "Enterprise Air-Gapped",
    }
    expired_token = jwt.encode(expired_payload, private_key, algorithm="RS256")

    with pytest.raises(LicenseExpiredError):
        verify_license(token=expired_token, public_key_path=public_key_path)
