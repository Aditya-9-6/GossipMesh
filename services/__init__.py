"""Services package for GossipMesh."""

try:
    from .key_pool_router import router, KeyPoolRouter, track_error_rate, KeyRouter, KeyMetrics, mask_key
except ImportError:
    mask_key = lambda k: k

__all__ = ["router", "KeyPoolRouter", "track_error_rate", "KeyRouter", "KeyMetrics"]
