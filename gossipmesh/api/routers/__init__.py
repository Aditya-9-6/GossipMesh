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

for mod in (
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
):
    if hasattr(mod, "router") and isinstance(getattr(mod, "router"), APIRouter):
        router.include_router(mod.router)
