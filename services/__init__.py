"""Root-level services package facade for backward compatibility and clean importing."""

from gossipmesh.services.key_pool_router import (
    KeyPoolRouter,
    KeyRouter,
    KeyMetrics,
    router,
    track_error_rate,
    mask_key,
)

__all__ = [
    "KeyPoolRouter",
    "KeyRouter",
    "KeyMetrics",
    "router",
    "track_error_rate",
    "mask_key",
]
