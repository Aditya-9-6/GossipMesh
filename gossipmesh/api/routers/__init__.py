from fastapi import APIRouter
from gossipmesh.api.routers import (
    auth,
    billing,
    organizations,
    projects,
    providers,
    repositories,
)

router = APIRouter()

router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(projects.router)
router.include_router(repositories.router)
router.include_router(providers.router)

__all__ = [
    "router",
    "auth",
    "billing",
    "organizations",
    "projects",
    "providers",
    "repositories",
]
