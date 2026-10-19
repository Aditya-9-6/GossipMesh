import time
from pathlib import Path
import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from enterprise.licensing import (
    verify_license,
    get_license_token,
    load_public_key,
    LicenseExpiredError,
    LicenseInvalidError,
    LicenseBundleError,
    LicenseTaskModelError,
)


@pytest.fixture
def private_key():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )


@pytest.fixture
def public_key(private_key):
    return private_key.public_key()


@pytest.fixture
def valid_license_token(private_key):
    now = int(time.time())
    payload = {
        "iss": "GossipMesh Enterprise Licensing Authority",
        "sub": "acme-corp",
        "iat": now - 3600,
        "exp": now + 86400,
        "bundle_ids": ["b01", "b02", "b03", "b04"],
        "task_model_map": {},
        "pricing_usd": 50000,
        "offline_air_gapped": True,
        "version": "1.0",
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def test_valid_offline_license_verification(valid_license_token, monkeypatch, public_key):
    """Ensure a properly signed RSA-4096 license validates offline."""
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    monkeypatch.setenv("GOSSIPMESH_LICENSE_PUBLIC_KEY", pub_bytes.decode("utf-8"))
    payload = verify_license(token=valid_license_token, required_bundle="b04")
    assert payload["sub"] == "acme-corp"
    assert "b04" in payload["bundle_ids"]


def test_expired_license_error(private_key, monkeypatch, public_key):
    """Ensure expired license raises LicenseExpiredError."""
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    monkeypatch.setenv("GOSSIPMESH_LICENSE_PUBLIC_KEY", pub_bytes.decode("utf-8"))
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
        verify_license(token=expired_token)
