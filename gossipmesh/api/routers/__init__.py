from typing import Any


class _RouterProxy:
    def __getattr__(self, name: str) -> Any:
        import importlib

        mod = importlib.import_module(f"gossipmesh.api.routers.{name}")
        return mod


auth = _RouterProxy()
organizations = _RouterProxy()
projects = _RouterProxy()
repositories = _RouterProxy()
providers = _RouterProxy()
billing = _RouterProxy()
router = _RouterProxy()

__all__ = [
    "auth",
    "organizations",
    "projects",
    "repositories",
    "providers",
    "billing",
    "router",
]
