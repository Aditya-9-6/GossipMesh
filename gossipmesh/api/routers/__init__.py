from typing import Any
from fastapi import APIRouter
from gossipmesh.api.routers import (
    auth,
    organizations,
    projects,
    repositories,
    providers,
    billing,
    enterprise,
)


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

router = APIRouter()

router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(projects.router)
router.include_router(repositories.router)
router.include_router(providers.router)
router.include_router(billing.router)
router.include_router(enterprise.router)

__all__ = [
    "router",
    "auth",
    "organizations",
    "projects",
    "repositories",
    "providers",
    "billing",
    "enterprise",
]
