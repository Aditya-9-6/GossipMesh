"""
Billing and commercialization for GossipMesh.
"""

from typing import Any

StripeBillingService: Any
try:
    from gossipmesh.billing.stripe_service import StripeBillingService

    __all__ = ["StripeBillingService"]
except ImportError:
    StripeBillingService = Any
    __all__ = []
