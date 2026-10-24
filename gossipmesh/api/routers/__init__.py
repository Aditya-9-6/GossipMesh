from fastapi import APIRouter
from gossipmesh.api.routers import (
    auth,
    organizations,
    projects,
    repositories,
    providers,
    enterprise,
)

try:
    from gossipmesh.api.routers import billing
except ImportError:
    billing = None  # type: ignore

router = APIRouter()

router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(projects.router)
router.include_router(repositories.router)
router.include_router(providers.router)
router.include_router(enterprise.router)

if billing is not None and hasattr(billing, "router"):
    router.include_router(billing.router)

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
