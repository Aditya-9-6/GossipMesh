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
        enterprise,
    )
from gossipmesh.api.routers import auth
from gossipmesh.api.routers import organizations
from gossipmesh.api.routers import projects
from gossipmesh.api.routers import repositories
from gossipmesh.api.routers import providers
from gossipmesh.api.routers import billing
from gossipmesh.api.routers import enterprise

router = APIRouter()

try:
    from gossipmesh.api.routers import auth

    router.include_router(auth.router)
except ImportError:
    auth = None  # type: ignore

try:
    from gossipmesh.api.routers import organizations

    router.include_router(organizations.router)
except ImportError:
    organizations = None  # type: ignore

try:
    from gossipmesh.api.routers import projects

    router.include_router(projects.router)
except ImportError:
    projects = None  # type: ignore

try:
    from gossipmesh.api.routers import repositories

    router.include_router(repositories.router)
except ImportError:
    repositories = None  # type: ignore

try:
    from gossipmesh.api.routers import providers

    router.include_router(providers.router)
except ImportError:
    providers = None  # type: ignore

try:
    from gossipmesh.api.routers import billing

    router.include_router(billing.router)
except ImportError:
    billing = None  # type: ignore

try:
    from gossipmesh.api.routers import enterprise

    router.include_router(enterprise.router)
except ImportError:
    enterprise = None  # type: ignore

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
