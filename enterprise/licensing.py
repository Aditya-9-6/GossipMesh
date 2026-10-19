import os
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


class LicenseError(Exception):
    """Base exception for licensing errors."""

    pass


class LicenseExpiredError(LicenseError):
    """Raised when a license has expired."""

    pass


class LicenseInvalidError(LicenseError):
    """Raised when a license is cryptographically invalid or tampered."""

    pass


class LicenseBundleError(LicenseError):
    """Raised when the license does not authorize the requested bundle."""

    pass


class LicenseTaskError(LicenseError):
    """Raised when the task-to-model mapping is violated."""

    pass


# Alias for backward compatibility with tests expecting LicenseTaskModelError
LicenseTaskModelError = LicenseTaskError


def get_license_token(token: Optional[str] = None, token_path: Optional[Path] = None) -> str:
    """
    Retrieve the license token from parameter, environment variable, file path, or default location.
    """
    if token:
        return token

    env_token = os.environ.get("GOSSIPMESH_LICENSE_TOKEN")
    if env_token:
        return env_token

    if token_path and token_path.exists():
        return token_path.read_text().strip()

    default_path = Path("/etc/gossipmesh/license.jwt")
    if default_path.exists():
        return default_path.read_text().strip()

    default_local_path = Path("license.jwt")
    if default_local_path.exists():
        return default_local_path.read_text().strip()

    raise LicenseInvalidError("No license token provided or found in environment/paths.")


def load_public_key(public_key_path: Optional[Path] = None) -> rsa.RSAPublicKey:
    """
    Load the RSA public key used to verify offline license tokens.
    """
    pub_key_str = None
    if public_key_path and public_key_path.exists():
        pub_key_str = public_key_path.read_text()
    else:
        pub_key_str = os.environ.get("GOSSIPMESH_LICENSE_PUBLIC_KEY")

    if not pub_key_str:
        default_pub_path = Path("/etc/gossipmesh/pubkey.pem")
        if default_pub_path.exists():
            pub_key_str = default_pub_path.read_text()

    if not pub_key_str:
        default_local_pub = Path("pubkey.pem")
        if default_local_pub.exists():
            pub_key_str = default_local_pub.read_text()

    if not pub_key_str:
        raise LicenseInvalidError(
            "No license public key provided via public_key_path, GOSSIPMESH_LICENSE_PUBLIC_KEY, or default paths."
        )

    try:
        if isinstance(pub_key_str, str):
            pub_key_bytes = pub_key_str.encode("utf-8")
        else:
            pub_key_bytes = pub_key_str

        public_key = serialization.load_pem_public_key(pub_key_bytes, backend=default_backend())
        if not isinstance(public_key, rsa.RSAPublicKey):
            raise LicenseInvalidError("Provided public key is not an RSA public key.")
        return public_key
    except Exception as e:
        raise LicenseInvalidError(f"Failed to load RSA public key: {e}") from e


def verify_license(
    token: Optional[str] = None,
    token_path: Optional[Path] = None,
    public_key_path: Optional[Path] = None,
    required_bundle: Optional[str] = None,
    required_task: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Cryptographically verify the offline license token using RSA-4096 (RS256).
    Enforces expiration, authorized bundles, and optional task-to-model mapping.

    Returns the decoded claims dictionary.
    """
    raw_token = get_license_token(token=token, token_path=token_path)
    public_key = load_public_key(public_key_path)

    try:
        payload = jwt.decode(
            raw_token,
            public_key,
            algorithms=["RS256"],
            options={
                "verify_signature": True,
                "require": ["exp", "sub", "bundle_ids"],
                "enforce_minimum_key_length": False,
            },
        )
    except jwt.ExpiredSignatureError as e:
        raise LicenseExpiredError(f"License has expired: {e}") from e
    except jwt.InvalidSignatureError as e:
        raise LicenseInvalidError(f"Cryptographic signature verification failed (tampered token): {e}") from e
    except jwt.PyJWTError as e:
        raise LicenseInvalidError(f"License verification failed: {e}") from e

    bundle_ids = payload.get("bundle_ids", [])
    if required_bundle and required_bundle not in bundle_ids:
        raise LicenseBundleError(
            f"Required bundle '{required_bundle}' not authorized by license. Authorized bundles: {bundle_ids}"
        )

    if required_task:
        task_map = payload.get("task_model_map", {})
        if required_task not in task_map:
            raise LicenseTaskError(f"Required task '{required_task}' is not authorized or mapped in the license.")

    return payload
