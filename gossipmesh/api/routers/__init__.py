from typing import Any
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


class _RouterProxy:
    def __getattr__(self, name: str) -> Any:
        import importlib

        try:
            mod = importlib.import_module(f"gossipmesh.api.routers.{name}")
            return mod
        except ImportError:
            return APIRouter()


auth = _RouterProxy()
organizations = _RouterProxy()
projects = _RouterProxy()
repositories = _RouterProxy()
providers = _RouterProxy()
billing = _RouterProxy()
enterprise = _RouterProxy()

router = APIRouter()

try:
    from gossipmesh.api.routers import auth as auth_mod

    if hasattr(auth_mod, "router"):
        router.include_router(auth_mod.router)
except Exception:
    pass

try:
    from gossipmesh.api.routers import organizations as orgs_mod

    if hasattr(orgs_mod, "router"):
        router.include_router(orgs_mod.router)
except Exception:
    pass

try:
    from gossipmesh.api.routers import projects as proj_mod

    if hasattr(proj_mod, "router"):
        router.include_router(proj_mod.router)
except Exception:
    pass

try:
    from gossipmesh.api.routers import repositories as repo_mod

    if hasattr(repo_mod, "router"):
        router.include_router(repo_mod.router)
except Exception:
    pass

try:
    from gossipmesh.api.routers import providers as prov_mod

    if hasattr(prov_mod, "router"):
        router.include_router(prov_mod.router)
except Exception:
    pass

try:
    from gossipmesh.api.routers import billing as bill_mod

    if hasattr(bill_mod, "router"):
        router.include_router(bill_mod.router)
except Exception:
    pass

try:
    from gossipmesh.api.routers import enterprise as ent_mod

    if hasattr(ent_mod, "router"):
        router.include_router(ent_mod.router)
except Exception:
    pass

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
