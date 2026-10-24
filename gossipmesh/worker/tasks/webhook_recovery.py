from gossipmesh.core.config import settings


def recover_webhooks() -> None:
    _ = settings.DATABASE_URL
