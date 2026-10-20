import datetime
import hmac
import hashlib
import json
import base64
from typing import Dict, Any, Optional


def verify_license(license_key: str, public_key_input: Optional[Any] = None) -> Dict[str, Any]:
    """
    Verifies an offline enterprise license key signature, expiration date, and payload.
    """
    try:
        parts = license_key.split(".")
        if len(parts) != 2:
            return {"valid": False, "error": "Invalid license format"}

        payload_b64, signature_hex = parts

        # Decode payload
        padding = "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8")
        data = json.loads(payload_json)

        # Check expiration
        expires_at_str = data.get("expires_at")
        if expires_at_str:
            expires_at = datetime.datetime.fromisoformat(expires_at_str)
            if datetime.datetime.utcnow() > expires_at:
                return {
                    "valid": False,
                    "error": "License expired",
                    "org_id": data.get("org_id"),
                    "tier": data.get("tier"),
                }

        # Verify signature using shared secret / public key representation
        expected_sig = hmac.new(
            b"gossipmesh-enterprise-secret-key", payload_b64.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, signature_hex):
            return {"valid": False, "error": "Invalid signature"}

        return {
            "valid": True,
            "org_id": data.get("org_id"),
            "tier": data.get("tier"),
            "seats": data.get("seats"),
            "expires_at": expires_at_str,
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}
