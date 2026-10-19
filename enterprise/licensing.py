"""
Enterprise Offline Cryptographic Licensing Module
=================================================
Validates RSA-4096 signed JWT license tokens offline.
Zero outbound network calls required — built specifically for
defense, fintech, and strict air-gapped environments.
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


class LicenseError(Exception):
    """Base exception for all licensing errors."""
    pass


class LicenseMissingError(LicenseError):
    """Raised when no license token or file is found."""
    pass


class LicenseExpiredError(LicenseError):
    """Raised when the license has expired."""
    pass


class LicenseInvalidError(LicenseError):
    """Raised when the signature or payload is tampered/invalid."""
    pass


class BundleNotAuthorizedError(LicenseError):
    """Raised when the license does not grant access to the requested model bundle."""
    pass


def _find_public_key_path() -> Path:
    """Find the public key file path in standard package locations."""
    # 1. Environment variable override
    env_path = os.getenv("LICENSE_PUBLIC_KEY_PATH")
    if env_path and Path(env_path).is_file():
        return Path(env_path)

    # 2. Adjacent to this file
    local_path = Path(__file__).parent / "public_key.pem"
    if local_path.is_file():
        return local_path

    # 3. Docker /app location or current working directory
    cwd_path = Path.cwd() / "enterprise" / "public_key.pem"
    if cwd_path.is_file():
        return cwd_path

    # 4. Standard container root
    container_path = Path("/app/enterprise/public_key.pem")
    if container_path.is_file():
        return container_path

    raise FileNotFoundError(
        f"RSA-4096 public key not found. Expected at {local_path} or set LICENSE_PUBLIC_KEY_PATH."
    )


def load_public_key(key_path: Optional[Path] = None):
    """Load and parse the RSA public key in PEM format."""
    target_path = key_path or _find_public_key_path()
    pem_data = target_path.read_bytes()
    return serialization.load_pem_public_key(pem_data, backend=default_backend())


def get_license_token(token: Optional[str] = None, token_path: Optional[Path] = None) -> str:
    """
    Retrieve the raw JWT license token string from:
    1. Direct argument
    2. LICENSE_TOKEN environment variable
    3. license.jwt in current directory or token_path
    4. license.token in current directory
    """
    if token and token.strip():
        return token.strip()

    env_token = os.getenv("LICENSE_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()

    if token_path:
        p = Path(token_path)
        if p.is_file():
            content = p.read_text(encoding="utf-8").strip()
            if content:
                return content
        raise LicenseMissingError(f"Specified license token file not found: {token_path}")

    search_paths = [
        Path.cwd() / "license.jwt",
        Path.cwd() / "license.token",
        Path("/app/license.jwt"),
        Path("/app/license.token"),
    ]

    for path in search_paths:
        if path.is_file():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                return content

    raise LicenseMissingError(
        "Missing license token. Please provide LICENSE_TOKEN environment variable "
        "or a license.jwt / license.token file in the working directory."
    )


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
            options={"require": ["exp", "sub", "bundle_ids"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise LicenseExpiredError(f"License has expired: {e}") from e
    except jwt.InvalidSignatureError as e:
        raise LicenseInvalidError(f"Cryptographic signature verification failed (tampered token): {e}") from e
    except jwt.PyJWTError as e:
        raise LicenseInvalidError(f"Invalid license token format: {e}") from e

    # Validate authorized bundles
    allowed_bundles = [b.lower().strip() for b in payload.get("bundle_ids", [])]
    task_map = {k.lower(): v.lower() for k, v in payload.get("task_model_map", {}).items()}

    if required_bundle:
        req_b = required_bundle.lower().strip()
        # Authorized if directly listed or if assigned in task map
        is_allowed = (req_b in allowed_bundles) or (req_b in task_map.values())
        if not is_allowed:
            raise BundleNotAuthorizedError(
                f"License tier does not authorize bundle '{required_bundle}'. "
                f"Allowed bundles: {allowed_bundles}"
            )

    if required_task:
        req_t = required_task.lower().strip()
        if task_map and req_t in task_map:
            assigned_bundle = task_map[req_t]
            if assigned_bundle not in allowed_bundles:
                raise BundleNotAuthorizedError(
                    f"Task '{required_task}' is mapped to '{assigned_bundle}', "
                    f"which is not authorized in this license."
                )

    return payload


def get_bundle_for_task(payload: Dict[str, Any], task: str, fallback_bundle: str = "b04") -> str:
    """
    Determine the authorized bundle ID for a given task.
    Respects customer's task_model_map if defined, otherwise falls back to
    first authorized bundle or the requested fallback.
    """
    task_map = payload.get("task_model_map") or {}
    task_clean = task.lower().strip()

    if task_clean in task_map:
        return task_map[task_clean].lower().strip()

    allowed = payload.get("bundle_ids", [])
    if allowed:
        # If fallback is in allowed list, use it
        if fallback_bundle.lower().strip() in [b.lower().strip() for b in allowed]:
            return fallback_bundle.lower().strip()
        return allowed[0].lower().strip()

    return fallback_bundle.lower().strip()
