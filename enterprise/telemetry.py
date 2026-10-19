"""
Enterprise SaaS Telemetry Module (Optional)
===========================================
Provides optional usage reporting for managed cloud customers.
Designed with strict air-gap safety:
- Completely disabled if SAAS_ENDPOINT is unset or AIR_GAPPED=1.
- Signs payloads with HMAC-SHA256 for integrity.
- Never raises exceptions or interrupts the reviewer if network fails.
"""

import os
import json
import time
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("enterprise.telemetry")

DEFAULT_ENDPOINT = "https://api.yourdomain.com/v1/telemetry"
DEFAULT_SECRET = "hmac_secret_key_placeholder"


def is_telemetry_enabled() -> bool:
    """Check if SaaS telemetry reporting is actively enabled."""
    if os.getenv("AIR_GAPPED", "").lower() in ("1", "true", "yes"):
        return False
    endpoint = os.getenv("SAAS_ENDPOINT")
    return bool(endpoint and endpoint.strip())


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for SaaS payload authentication."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


def report_telemetry_event(
    customer_id: str,
    event_type: str,
    bundle_id: str,
    task_type: str,
    metrics: Optional[Dict[str, Any]] = None,
    timeout_seconds: float = 3.0,
) -> bool:
    """
    Send an asynchronous-safe telemetry event to the SaaS backend.
    
    Returns True if successfully sent, False if disabled or failed.
    Guaranteed NEVER to raise an exception.
    """
    if not is_telemetry_enabled():
        logger.debug("[Telemetry] Disabled (air-gapped or no SAAS_ENDPOINT configured).")
        return False

    endpoint = os.getenv("SAAS_ENDPOINT", DEFAULT_ENDPOINT).strip()
    secret = os.getenv("SAAS_TELEMETRY_SECRET", DEFAULT_SECRET).strip()

    data = {
        "customer_id": customer_id,
        "event_type": event_type,
        "bundle_id": bundle_id,
        "task_type": task_type,
        "timestamp": int(time.time()),
        "metrics": metrics or {},
    }

    try:
        import httpx
        payload_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
        signature = sign_payload(payload_bytes, secret)

        headers = {
            "Content-Type": "application/json",
            "X-GossipMesh-Customer": customer_id,
            "X-GossipMesh-Signature": signature,
        }

        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(endpoint, content=payload_bytes, headers=headers)
            if resp.status_code in (200, 201, 202, 204):
                logger.info(f"[Telemetry] Successfully reported {event_type} to {endpoint}")
                return True
            else:
                logger.warning(f"[Telemetry] Server returned HTTP {resp.status_code}: {resp.text[:100]}")
                return False

    except Exception as exc:
        # Crucial for air-gap defense / offline resilience: never break reviewer on network issues
        logger.debug(f"[Telemetry] Safely skipped due to network or connection issue: {exc}")
        return False
