import time
import pytest
import jwt
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from enterprise.licensing import verify_license, LicenseExpiredError, LicenseInvalidError, DEFAULT_PUBLIC_KEY_PATH


@pytest.fixture
def private_key():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture
def public_key_pem(private_key):
    pub_key = private_key.public_key()
    return pub_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")


@pytest.fixture
def valid_license_token(private_key):
    now = int(time.time())
    payload = {
        "iss": "GossipMesh Enterprise Licensing Authority",
        "sub": "acme-corp",
        "iat": now,
        "exp": now + 7200,
        "bundle_ids": ["b04"],
        "tier": "Enterprise Air-Gapped",
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


@pytest.fixture(autouse=True)
def setup_licensing_env(monkeypatch, public_key_pem, tmp_path):
    key_file = tmp_path / "licensing_public.pem"
    key_file.write_text(public_key_pem)
    monkeypatch.setattr("enterprise.licensing.DEFAULT_PUBLIC_KEY_PATH", key_file)
    monkeypatch.setenv("GOSSIPMESH_TEST_PUBLIC_KEY", public_key_pem)


def test_valid_offline_license_verification(valid_license_token):
    """Ensure a properly signed RSA license validates offline."""
    payload = verify_license(token=valid_license_token, required_bundle="b04")
    assert payload["sub"] == "acme-corp"


def test_expired_license_error(private_key):
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
        verify_license(token=expired_token)


def test_tampered_license_signature(valid_license_token):
    """Ensure tampered tokens or payload mutations fail cryptographic signature verification."""
    tampered_token = valid_license_token[:-6] + "XYZ123"

    with pytest.raises(LicenseInvalidError):
        verify_license(token=tampered_token)
