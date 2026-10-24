from typing import Any, TYPE_CHECKING
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
    auth = None  # type: ignore

try:
    from gossipmesh.api.routers import organizations as orgs_mod

    if hasattr(orgs_mod, "router"):
        router.include_router(orgs_mod.router)
except Exception:
    organizations = None  # type: ignore

try:
    from gossipmesh.api.routers import projects as proj_mod

    if hasattr(proj_mod, "router"):
        router.include_router(proj_mod.router)
except Exception:
    projects = None  # type: ignore

try:
    from gossipmesh.api.routers import repositories as repo_mod

    if hasattr(repo_mod, "router"):
        router.include_router(repo_mod.router)
except Exception:
    repositories = None  # type: ignore

try:
    from gossipmesh.api.routers import providers as prov_mod

    if hasattr(prov_mod, "router"):
        router.include_router(prov_mod.router)
except Exception:
    providers = None  # type: ignore

try:
    from gossipmesh.api.routers import billing as bill_mod

    if hasattr(bill_mod, "router"):
        router.include_router(bill_mod.router)
except Exception:
    billing = None  # type: ignore

try:
    from gossipmesh.api.routers import enterprise as ent_mod

    if hasattr(ent_mod, "router"):
        router.include_router(ent_mod.router)
except Exception:
    enterprise = None  # type: ignore

try:
    from gossipmesh.api.routers import approvals

    if hasattr(approvals, "router"):
        router.include_router(approvals.router)
except Exception:
    approvals = None  # type: ignore

try:
    from gossipmesh.api.routers import users

    if hasattr(users, "router"):
        router.include_router(users.router)
except Exception:
    users = None  # type: ignore

try:
    from gossipmesh.api.routers import runtime

    if hasattr(runtime, "router"):
        router.include_router(runtime.router)
except Exception:
    runtime = None  # type: ignore

try:
    from gossipmesh.api.routers import artifacts

    if hasattr(artifacts, "router"):
        router.include_router(artifacts.router)
except Exception:
    artifacts = None  # type: ignore

try:
    from gossipmesh.api.routers import vector_search

    if hasattr(vector_search, "router"):
        router.include_router(vector_search.router)
except Exception:
    vector_search = None  # type: ignore

try:
    from gossipmesh.api.routers import service_accounts

    if hasattr(service_accounts, "router"):
        router.include_router(service_accounts.router)
except Exception:
    service_accounts = None  # type: ignore

try:
    from gossipmesh.api.routers import sso

    if hasattr(sso, "router"):
        router.include_router(sso.router)
except Exception:
    sso = None  # type: ignore

try:
    from gossipmesh.api.routers import scim

    if hasattr(scim, "router"):
        router.include_router(scim.router)
except Exception:
    scim = None  # type: ignore

try:
    from gossipmesh.api.routers import runs

    if hasattr(runs, "router"):
        router.include_router(runs.router)
except Exception:
    runs = None  # type: ignore

try:
    from gossipmesh.api.routers import health

    if hasattr(health, "router"):
        router.include_router(health.router)
except Exception:
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
