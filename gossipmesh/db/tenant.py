"""Tenant-scoped queries, context isolation, and cross-organization guards (Task 35).
Enforces strict multi-tenant boundary checks across:
- Relational database queries
- RAG and vector embeddings
- Semantic caches
- Artifacts and workspace directories
- Audit logs and event ledgers
"""

import contextvars
from typing import Any, Dict, List, Optional, Type
from sqlalchemy.orm import Query, Session

from gossipmesh.core.exceptions import AuthorizationError
from gossipmesh.models.user import User

# ContextVar for thread/async-safe tenant context propagation
current_tenant_id: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar("current_tenant_id", default=None)


class TenantContext:
    """Context manager to establish active tenant boundaries."""

    def __init__(self, organization_id: int):
        self.org_id = organization_id
        self._token: Optional[contextvars.Token] = None

    def __enter__(self):
        self._token = current_tenant_id.set(self.org_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            current_tenant_id.reset(self._token)


class TenantQueryGuard:
    """Enforces tenant-scoped database queries and isolation policies."""

    @staticmethod
    def get_current_tenant_id() -> Optional[int]:
        return current_tenant_id.get()

    @staticmethod
    def assert_tenant_access(user: User, organization_id: int):
        """Asserts that the user belongs to the target organization or is superuser."""
        if getattr(user, "is_superuser", False):
            return

        user_org_ids = []
        for org in getattr(user, "organizations", []):
            if hasattr(org, "organization_id"):
                user_org_ids.append(org.organization_id)
            elif hasattr(org, "id"):
                user_org_ids.append(org.id)

        if hasattr(user, "organization_id") and user.organization_id:
            user_org_ids.append(user.organization_id)

        if organization_id not in user_org_ids:
            raise AuthorizationError(
                message=f"Access denied: User {user.id} does not have access to organization {organization_id}"
            )

    @classmethod
    def filter_query(
        cls,
        db: Session,
        model: Type[Any],
        organization_id: Optional[int] = None,
    ) -> Query:
        """Constructs a query strictly bound to an organization to prevent cross-tenant leakage."""
        active_org = organization_id or cls.get_current_tenant_id()
        if active_org is None:
            raise AuthorizationError(
                message="Tenant isolation violation: Cannot execute query without active organization scope."
            )

        model_name = getattr(model, "__name__", str(model))

        # Check scoping path first before issuing query
        has_scoping = (
            hasattr(model, "organization_id")
            or (model_name == "Organization" and hasattr(model, "id"))
            or hasattr(model, "repository_id")
            or hasattr(model, "workflow_id")
            or hasattr(model, "project_id")
        )
        if not has_scoping:
            raise ValueError(f"Model {model_name} has no defined organization scoping path.")

        query = db.query(model)

        # 1. Direct organization_id column
        if hasattr(model, "organization_id"):
            return query.filter(model.organization_id == active_org)

        # 2. Model is Organization itself
        if model_name == "Organization" and hasattr(model, "id"):
            return query.filter(model.id == active_org)

        # 3. Model is linked through Repository (e.g. DocumentChunk)
        if hasattr(model, "repository_id"):
            from gossipmesh.models.repository import Repository

            return query.join(Repository, model.repository_id == Repository.id).filter(
                Repository.organization_id == active_org
            )

        # 4. Model is linked through Workflow (e.g. Job)
        if hasattr(model, "workflow_id"):
            from gossipmesh.models.runtime import Workflow

            return query.join(Workflow, model.workflow_id == Workflow.id).filter(Workflow.organization_id == active_org)

        # 5. Model is linked through Project
        if hasattr(model, "project_id"):
            from gossipmesh.models.project import Project

            return query.join(Project, model.project_id == Project.id).filter(Project.organization_id == active_org)

        raise ValueError(f"Model {model_name} has no defined organization scoping path.")

    @staticmethod
    def scope_cache_key(key: str, organization_id: int) -> str:
        """Prefixes semantic cache keys with tenant ID to prevent cross-organization cache hits."""
        return f"tenant:{organization_id}:cache:{key}"

    @staticmethod
    def scope_vector_filter(organization_id: int, base_filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Injects organization boundary into vector search filters."""
        res = dict(base_filter or {})
        res["organization_id"] = organization_id
        return res

    @staticmethod
    def scope_artifact_path(organization_id: int, filename: str) -> str:
        """Sanitizes and partitions artifact paths by organization."""
        parts = [p for p in filename.replace("\\", "/").split("/") if p and p != ".." and p != "."]
        clean_name = "/".join(parts)
        return f"artifacts/{organization_id}/{clean_name}"
