from fastapi import APIRouter
from gossipmesh.api.routers import (
    approvals,
    auth,
    billing,
    organizations,
    projects,
    providers,
    repositories,
    webhooks,
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

router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(projects.router)
router.include_router(repositories.router)
router.include_router(providers.router)
router.include_router(billing.router)
router.include_router(enterprise.router)

__all__ = [
    "router",
    "approvals",
    "auth",
    "billing",
    "organizations",
    "projects",
    "providers",
    "repositories",
    "webhooks",
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
