import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
import jwt


class LicenseError(Exception):
    """Base exception for all enterprise licensing errors."""

    pass


class LicenseExpiredError(LicenseError):
    """Raised when the license token has expired."""

    pass


class LicenseInvalidError(LicenseError):
    """Raised when the license token is cryptographically invalid or tampered."""

    pass


class LicenseBundleError(LicenseError):
    """Raised when the license does not contain a required bundle."""

    pass


class BundleNotAuthorizedError(LicenseBundleError):
    """Raised when a specific bundle is not authorized."""

    pass


class LicenseTaskError(LicenseError):
    """Raised when the license does not authorize a required model/task."""

    pass


class LicenseNotFoundError(LicenseError):
    """Raised when no license token or file is provided or found."""

    pass


# Alias for compatibility with tests expecting LicenseMissingError
LicenseMissingError = LicenseNotFoundError


DEFAULT_LICENSE_PATH = Path("/etc/gossipmesh/license.jwt")
DEFAULT_PUBLIC_KEY_PATH = Path("/etc/gossipmesh/licensing_public.pem")


def get_license_token(
    token: Optional[str] = None,
    token_path: Optional[Path] = None,
) -> str:
    """
    Retrieves the raw JWT license token from direct argument, environment variable,
    or a file path on disk.
    """
    if token:
        return token.strip()

    path = token_path or DEFAULT_LICENSE_PATH
    if path.exists():
        try:
            content = path.read_text(encoding="utf-8").strip()
            if content:
                return content
        except Exception as e:
            raise LicenseNotFoundError(f"Failed to read license file at {path}: {e}") from e

    raise LicenseNotFoundError("No enterprise license token provided via argument or found at default path.")


def load_public_key(public_key_path: Optional[Path] = None) -> str:
    """
    Loads the RSA public key used to verify the enterprise license token.
    """
    path = public_key_path or DEFAULT_PUBLIC_KEY_PATH
    if not path.exists():
        raise LicenseNotFoundError(f"Enterprise licensing public key not found at {path}.")
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        raise LicenseInvalidError(f"Failed to load public key from {path}: {e}") from e


def get_bundle_for_task(
    payload: Dict[str, Any],
    task_name: str,
    fallback_bundle: Optional[str] = None,
) -> str:
    """Resolves which bundle authorizes a given task."""
    task_map = payload.get("task_model_map", {})
    if isinstance(task_map, dict) and task_name in task_map:
        return task_map[task_name]
    if fallback_bundle:
        return fallback_bundle
    raise LicenseTaskError(f"No bundle found for task: {task_name}")


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
            options={"verify_signature": True, "verify_exp": True, "require": ["exp", "sub", "bundle_ids"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise LicenseExpiredError(f"License has expired: {e}") from e
    except jwt.InvalidSignatureError as e:
        raise LicenseInvalidError(f"Cryptographic signature verification failed (tampered token): {e}") from e
    except jwt.PyJWTError as e:
        raise LicenseInvalidError(f"Invalid license token: {e}") from e

    # Enforce required feature bundle if specified
    if required_bundle:
        bundle_ids = payload.get("bundle_ids", [])
        if not isinstance(bundle_ids, list) or required_bundle not in bundle_ids:
            raise BundleNotAuthorizedError(f"License does not authorize bundle '{required_bundle}'.")

    # Enforce optional task-to-model mapping authorization
    if required_task:
        task_map = payload.get("task_model_map", {})
        if not isinstance(task_map, dict) or required_task not in task_map:
            raise LicenseTaskError(f"License does not authorize required model task: {required_task}")

    return payload
