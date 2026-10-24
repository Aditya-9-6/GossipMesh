from typing import TYPE_CHECKING
from fastapi import APIRouter

if TYPE_CHECKING:
    from gossipmesh.api.routers import (
        approvals,
        auth,
        billing,
        organizations,
        projects,
        providers,
        repositories,
        users,
        runtime,
        artifacts,
        enterprise,
        vector_search,
        service_accounts,
        sso,
        scim,
        runs,
        health,
    )

from gossipmesh.api.routers import (
    approvals,
    auth,
    billing,
    organizations,
    projects,
    providers,
    repositories,
    users,
    runtime,
    artifacts,
    enterprise,
    vector_search,
    service_accounts,
    sso,
    scim,
    runs,
    health,
)

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

try:
    from gossipmesh.api.routers import approvals

    router.include_router(approvals.router)
except ImportError:
    approvals = None  # type: ignore

try:
    from gossipmesh.api.routers import users

    router.include_router(users.router)
except ImportError:
    users = None  # type: ignore

try:
    from gossipmesh.api.routers import runtime

    router.include_router(runtime.router)
except ImportError:
    runtime = None  # type: ignore

try:
    from gossipmesh.api.routers import artifacts

    router.include_router(artifacts.router)
except ImportError:
    artifacts = None  # type: ignore

try:
    from gossipmesh.api.routers import vector_search

    router.include_router(vector_search.router)
except ImportError:
    vector_search = None  # type: ignore

try:
    from gossipmesh.api.routers import service_accounts

    router.include_router(service_accounts.router)
except ImportError:
    service_accounts = None  # type: ignore

try:
    from gossipmesh.api.routers import sso

    router.include_router(sso.router)
except ImportError:
    sso = None  # type: ignore

try:
    from gossipmesh.api.routers import scim

    router.include_router(scim.router)
except ImportError:
    scim = None  # type: ignore

try:
    from gossipmesh.api.routers import runs

    router.include_router(runs.router)
except ImportError:
    runs = None  # type: ignore

try:
    from gossipmesh.api.routers import health

    router.include_router(health.router)
except ImportError:
    health = None  # type: ignore

__all__ = [
    "router",
    "approvals",
    "auth",
    "billing",
    "organizations",
    "projects",
    "providers",
    "repositories",
    "users",
    "runtime",
    "artifacts",
    "enterprise",
    "vector_search",
    "service_accounts",
    "sso",
    "scim",
    "runs",
    "health",
]
