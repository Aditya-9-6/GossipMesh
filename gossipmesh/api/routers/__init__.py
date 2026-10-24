from fastapi import APIRouter
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
