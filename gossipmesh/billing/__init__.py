"""
Billing package initialization.
"""

try:
    from gossipmesh.billing.stripe_service import StripeBillingService
except Exception:
    StripeBillingService = None  # type: ignore

__all__ = ["StripeBillingService"]
