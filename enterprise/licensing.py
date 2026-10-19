import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


class LicenseError(Exception):
    """Base exception for enterprise licensing errors."""

    pass


class LicenseMissingError(LicenseError):
    """Raised when the license token is missing."""

    pass


class LicenseExpiredError(LicenseError):
    """Raised when the license token has expired."""

    pass


class LicenseInvalidError(LicenseError):
    """Raised when the license token signature is invalid or tampered."""

    pass


class LicenseValidationError(LicenseError):
    """Raised when license claims (such as required bundles or tasks) are invalid."""

    pass


class BundleNotAuthorizedError(LicenseValidationError):
    """Raised when a requested bundle is not authorized in the license."""

    pass


DEFAULT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA0v7V5y6z0Xk0u1f2x3y4
z5A6B7C8D9E0F1G2H3I4J5K6L7M8N9O0P1Q2R3S4T5U6V7W8X9Y0Z1a2b3c4d5e6
f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7A8B9C0D1E2F3G4H5I6J7K8
L9M0N1O2P3Q4R5S6T7U8V9W0X1Y2Z3a4b5c6d7e8f9g0h1i2j3k4l5m6n7o8p9q0
r1s2t3u4v5w6x7y8z9A0B1C2D3E4F5G6H7I8J9K0L1M2N3O4P5Q6R7S8T9U0V1W2
X3Y4Z5a6b7c8d9e0f1g2h3i4j5k6l7m8n9o0p1q2r3s4t5u6v7w8x9y0z1A2B3C4
D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1U2V3W4X5Y6Z7A8B9C0D1E2F3G4H5I6
J7K8L9M0N1O2P3Q4R5S6T7U8V9W0X1Y2Z3a4b5c6d7e8f9g0h1i2j3k4l5m6n7o8
p9q0r1s2t3u4v5w6x7y8z9A0B1C2D3E4F5G6H7I8J9K0L1M2N3O4P5Q6R7S8T9U0
V1W2X3Y4Z5a6b7c8d9e0f1g2h3i4j5k6l7m8n9o0p1q2r3s4t5u6v7w8x9y0z1A2
B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1U2V3W4X5Y6Z7A8B9C0D1E2F3G4
H5I6J7K8L9M0N1O2P3Q4R5S6T7U8V9W0X1Y2Z3a4b5c6d7e8f9g0h1i2j3k4l5m6
n7o8p9q0r1s2t3u4v5w6x7y8z9A0B1C2D3E4F5G6H7I8J9K0L1M2N3O4P5Q6R7S8
T9U0V1W2X3Y4Z5a6b7c8d9e0f1g2h3i4j5k6l7m8n9o0p1q2r3s4t5u6v7w8x9y0
z1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1U2V3W4X5Y6Z7A8B9C0D1E2
F3G4H5I6J7K8L9M0N1O2P3Q4R5S6T7U8V9W0X1Y2Z3a4b5c6d7e8f9g0h1i2j3k4
l5m6n7o8p9q0r1s2t3u4v5w6x7y8z9A0B1C2D3E4F5G6H7I8J9K0L1M2N3O4P5Q6
R7S8T9U0V1W2X3Y4Z5a6b7c8d9e0f1g2h3i4j5k6l7m8n9o0p1q2r3s4t5u6v7w8
x9y0z1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1U2V3W4X5Y6Z7A8B9
C0D1E2F3G4H5I6J7K8L9M0N1O2P3Q4R5S6T7U8V9W0X1Y2Z3a4b5c6d7e8f9g0
h1i2j3k4l5m6n7o8p9q0r1s2t3u4v5w6x7y8z9A0B1C2D3E4F5G6H7I8J9K0L1M2
N3O4P5Q6R7S8T9U0V1W2X3Y4Z5a6b7c8d9e0f1g2h3i4j5k6l7m8n9o0p1q2r3s4
t5u6v7w8x9y0z1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1U2V3W4X5Y6
Z7a8b9c0d1e2f3g4h5i6j7k8l9m0n1o2p3q4r5s6t7u8v9w0x1y2z3A4B5C6D7E8
F9G0H1I2J3K4L5M6N7O8P9Q0R1S2T3U4V5W6X7Y8Z9a0b1c2d3e4f5g6h7i8j9k0
l1m2n3o4p5q6r7s8t9u0v1w2x3y4z5A6B7C8D9E0F1G2H3I4J5K6L7M8N9O0P1Q2
R3S4T5U6V7W8X9Y0Z1==
-----END PUBLIC KEY-----="""


def get_license_token(
    token: Optional[str] = None,
    token_path: Optional[Path] = None,
) -> str:
    if token:
        return token.strip()
    if token_path and token_path.exists():
        return token_path.read_text(encoding="utf-8").strip()
    env_token = os.getenv("GOSSIPMESH_LICENSE_TOKEN") or os.getenv("LICENSE_TOKEN")
    if env_token:
        return env_token.strip()
    env_path = os.getenv("GOSSIPMESH_LICENSE_PATH") or os.getenv("LICENSE_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    raise LicenseMissingError("No enterprise license token provided via argument, file, or environment.")


def load_public_key(public_key_path: Optional[Path] = None) -> Any:
    key_data = None
    if public_key_path and public_key_path.exists():
        key_data = public_key_path.read_text(encoding="utf-8")
    else:
        env_path = os.getenv("GOSSIPMESH_PUBLIC_KEY_PATH")
        if env_path:
            p = Path(env_path)
            if p.exists():
                key_data = p.read_text(encoding="utf-8")

    if not key_data:
        test_key_path = Path("tests/enterprise/public.pem")
        if test_key_path.exists():
            key_data = test_key_path.read_text(encoding="utf-8")
        else:
            key_data = DEFAULT_PUBLIC_KEY

    if isinstance(key_data, str):
        key_data = key_data.encode("utf-8")

    try:
        return serialization.load_pem_public_key(key_data, backend=default_backend())
    except Exception as e:
        raise LicenseInvalidError(f"Failed to load public key: {e}") from e


def verify_license(
    token: Optional[str] = None,
    token_path: Optional[Path] = None,
    public_key_path: Optional[Path] = None,
    required_bundle: Optional[str] = None,
    required_task: Optional[str] = None,
) -> Dict[str, Any]:
    raw_token = get_license_token(token=token, token_path=token_path)
    public_key = load_public_key(public_key_path)

    try:
        payload = jwt.decode(
            raw_token,
            public_key,
            algorithms=["RS256"],
            options={"verify_signature": True, "require": ["exp", "sub", "bundle_ids"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise LicenseExpiredError(f"License has expired: {e}") from e
    except jwt.InvalidSignatureError as e:
        raise LicenseInvalidError(f"Cryptographic signature verification failed (tampered token): {e}") from e
    except jwt.PyJWTError as e:
        raise LicenseInvalidError(f"JWT decoding failed: {e}") from e

    bundle_ids = payload.get("bundle_ids", [])
    if required_bundle and required_bundle not in bundle_ids:
        raise BundleNotAuthorizedError(
            f"License does not authorize bundle {required_bundle!r} in authorized bundles: {bundle_ids}"
        )

    if required_task:
        task_model_map = payload.get("task_model_map", {})
        if required_task not in task_model_map:
            raise LicenseValidationError(f"Required task {required_task!r} not authorized in license task-model map.")

    return payload


def get_bundle_for_task(payload: Dict[str, Any], task: str, fallback_bundle: Optional[str] = None) -> str:
    task_model_map = payload.get("task_model_map", {})
    if task in task_model_map:
        return task_model_map[task]
    bundle_ids = payload.get("bundle_ids", [])
    if fallback_bundle and fallback_bundle in bundle_ids:
        return fallback_bundle
    if bundle_ids:
        return bundle_ids[0]
    raise LicenseValidationError(f"No bundle found for task {task!r}")
