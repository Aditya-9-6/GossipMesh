"""
Billing and commercialization for GossipMesh.
"""

from typing import Any

BillingType: Any = object()


class BillingRouter:
    pass


router = BillingRouter()

StripeBillingService: Any
try:
    from gossipmesh.billing.stripe_service import StripeBillingService

    __all__ = ["StripeBillingService", "BillingRouter", "router", "BillingType"]
except ImportError:
    StripeBillingService = Any
    __all__ = ["BillingRouter", "router", "BillingType"]
