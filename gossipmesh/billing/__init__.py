"""
Billing package initialization.
"""

from typing import Any

StripeBillingService: Any
try:
    from gossipmesh.billing.stripe_service import StripeBillingService
except (ImportError, Exception):
    StripeBillingService = None  # type: ignore

__all__ = ["StripeBillingService"]
