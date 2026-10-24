"""
Billing and commercialization for GossipMesh.
"""

try:
    from gossipmesh.billing.stripe_service import StripeBillingService
except ImportError:
    StripeBillingService = None  # type: ignore

__all__ = ["StripeBillingService"]
