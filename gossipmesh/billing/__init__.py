from typing import Any


class StripeBillingService:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def create_checkout_session(self, *args: Any, **kwargs: Any) -> Any:
        return {}

    def create_billing_portal_session(self, *args: Any, **kwargs: Any) -> Any:
        return {}

    def get_active_subscription(self, *args: Any, **kwargs: Any) -> Any:
        return None

    def cancel_subscription(self, *args: Any, **kwargs: Any) -> Any:
        return None

    def list_invoices(self, *args: Any, **kwargs: Any) -> Any:
        return []

    def verify_webhook_signature(self, *args: Any, **kwargs: Any) -> Any:
        return {}

    def handle_webhook_event(self, *args: Any, **kwargs: Any) -> Any:
        return {}
