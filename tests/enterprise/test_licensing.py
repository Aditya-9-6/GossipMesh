"""
Unit Tests for Enterprise Offline Cryptographic Licensing Module
"""

import time
import pytest
from pathlib import Path
import jwt

from enterprise.licensing import (
    verify_license,
    get_bundle_for_task,
    load_public_key,
    LicenseMissingError,
    LicenseExpiredError,
    LicenseInvalidError,
    BundleNotAuthorizedError,
)
from scripts.issue_license import issue_license, load_private_key


@pytest.fixture
def private_key():
    """Load test private key."""
    key_path = Path(__file__).resolve().parent.parent.parent / "enterprise" / "test_private_key.pem"
    return load_private_key(str(key_path))


@pytest.fixture
def valid_license_token(private_key):
    """Generate a valid 1-year Enterprise B04 license token."""
    return issue_license(
        customer_id="acme-defense-corp",
        bundle_ids=["b04"],
        plan="1_year",
        private_key_path=str(Path(__file__).resolve().parent.parent.parent / "enterprise" / "test_private_key.pem"),
    )


def test_valid_offline_license_verification(valid_license_token):
    """Ensure a properly signed RSA-4096 license validates offline."""
    payload = verify_license(
        token=valid_license_token,
        public_key_path=Path(__file__).resolve().parent.parent.parent / "enterprise" / "test_public_key.pem",
        required_bundle="b04",
    )
    assert payload["sub"] == "acme-defense-corp"
    assert payload["tier"] == "Enterprise Air-Gapped"
    assert payload["plan"] == "1_year"
    assert payload["pricing_usd"] == 50_000
    assert payload["offline_air_gapped"] is True
    assert "b04" in payload["bundle_ids"]


def test_missing_license_error(monkeypatch):
    """Ensure missing license triggers LicenseMissingError."""
    monkeypatch.delenv("LICENSE_TOKEN", raising=False)
    with pytest.raises(LicenseMissingError):
        verify_license(token=None, token_path=Path("nonexistent_license.jwt"))


def test_expired_license_error(private_key):
    """Ensure expired license raises LicenseExpiredError."""
    now = int(time.time())
    expired_payload = {
        "iss": "GossipMesh Enterprise",
        "sub": "expired-corp",
        "iat": now - 7200,
        "exp": now - 3600,  # Expired 1 hour ago
        "bundle_ids": ["b04"],
        "tier": "Enterprise Air-Gapped",
    }
    expired_token = jwt.encode(expired_payload, private_key, algorithm="RS256")

    with pytest.raises(LicenseExpiredError):
        verify_license(
            token=expired_token,
            public_key_path=Path(__file__).resolve().parent.parent.parent / "enterprise" / "test_public_key.pem",
        )


def test_tampered_license_signature(valid_license_token):
    """Ensure tampered tokens or payload mutations fail cryptographic signature verification."""
    # Mutate the last few characters of the JWT signature
    tampered_token = valid_license_token[:-6] + "XYZ123"

    with pytest.raises(LicenseInvalidError):
        verify_license(
            token=tampered_token,
            public_key_path=Path(__file__).resolve().parent.parent.parent / "enterprise" / "test_public_key.pem",
        )


def test_bundle_not_authorized_error(valid_license_token):
    """Ensure requesting a higher tier bundle not in license raises BundleNotAuthorizedError."""
    # License has b04, client requests b05
    with pytest.raises(BundleNotAuthorizedError, match="does not authorize bundle 'b05'"):
        verify_license(
            token=valid_license_token,
            public_key_path=Path(__file__).resolve().parent.parent.parent / "enterprise" / "test_public_key.pem",
            required_bundle="b05",
        )


def test_task_to_model_resolution():
    """Ensure task-to-model mapping resolves correctly."""
    payload = {
        "bundle_ids": ["b01", "b04", "b05"],
        "task_model_map": {
            "syntax": "b01",
            "security": "b04",
            "architecture": "b04",
            "auto_remediation": "b05",
        },
    }

    assert get_bundle_for_task(payload, "syntax") == "b01"
    assert get_bundle_for_task(payload, "security") == "b04"
    assert get_bundle_for_task(payload, "architecture") == "b04"
    assert get_bundle_for_task(payload, "auto_remediation") == "b05"
    assert get_bundle_for_task(payload, "unknown_task", fallback_bundle="b04") == "b04"
