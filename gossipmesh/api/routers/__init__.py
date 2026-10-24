from typing import TYPE_CHECKING
from fastapi import APIRouter

if TYPE_CHECKING:
    from gossipmesh.api.routers import (
        auth,
        organizations,
        projects,
        repositories,
        providers,
        billing,
    )

from gossipmesh.api.routers import auth
from gossipmesh.api.routers import organizations
from gossipmesh.api.routers import projects
from gossipmesh.api.routers import repositories
from gossipmesh.api.routers import providers
from gossipmesh.api.routers import billing

router = APIRouter()

router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(projects.router)
router.include_router(repositories.router)
router.include_router(providers.router)
router.include_router(billing.router)

__all__ = [
    "router",
    "auth",
    "organizations",
    "projects",
    "repositories",
    "providers",
    "billing",
]
