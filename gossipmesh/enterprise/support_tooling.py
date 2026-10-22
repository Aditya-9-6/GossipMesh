"""
Customer Support Tooling & Operator Console (Task 125).

Provides authorized, break-glass bounded operator operations:
- Organization lookup
- Subsystem health inspection
- Failed workflow retry
- Audit log inspection
- Data export initiation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from gossipmesh.core.exceptions import AuthorizationError, ValidationError
from gossipmesh.enterprise.break_glass import BreakGlassControlService
from gossipmesh.enterprise.disaster_recovery import DisasterRecoveryService
from gossipmesh.models.audit import AuditEvent
from gossipmesh.models.organization import Organization, UserOrganization
from gossipmesh.models.repository import Repository
from gossipmesh.models.runtime import Job, Workflow


class CustomerSupportTooling:
    """Enterprise support operations bounded by break-glass authorization."""

    def __init__(self, break_glass_service: Optional[BreakGlassControlService] = None):
        self.break_glass = break_glass_service or BreakGlassControlService()

    def _require_authorized_session(self, support_user_id: int, organization_id: int) -> None:
        """Enforces that an active, non-expired break-glass session exists."""
        self.break_glass.verify_access(
            support_user_id=support_user_id,
            organization_id=organization_id,
            requesting_source_code=False,
        )

    def lookup_organization(
        self,
        session: Session,
        support_user_id: int,
        organization_id: int,
    ) -> Dict[str, Any]:
        """Looks up organization overview and member counts."""
        self._require_authorized_session(support_user_id, organization_id)
        org = session.get(Organization, organization_id)
        if not org:
            raise ValidationError(f"Organization ID {organization_id} not found")

        member_count = session.query(UserOrganization).filter_by(organization_id=organization_id).count()
        repo_count = session.query(Repository).filter_by(organization_id=organization_id).count()

        audit = AuditEvent(
            action="support.organization_lookup",
            actor_id=support_user_id,
            organization_id=organization_id,
            details={"member_count": member_count, "repo_count": repo_count},
        )
        session.add(audit)
        session.commit()

        return {
            "id": org.id,
            "name": org.name,
            "member_count": member_count,
            "repository_count": repo_count,
        }

    def inspect_health(
        self,
        session: Session,
        support_user_id: int,
        organization_id: int,
    ) -> Dict[str, Any]:
        """Inspects failure counts, active workflows, and execution health."""
        self._require_authorized_session(support_user_id, organization_id)

        failed_workflows = (
            session.query(Workflow)
            .filter(Workflow.organization_id == organization_id, Workflow.status == "failed")
            .count()
        )
        running_workflows = (
            session.query(Workflow)
            .filter(Workflow.organization_id == organization_id, Workflow.status == "running")
            .count()
        )

        return {
            "organization_id": organization_id,
            "failed_workflows_count": failed_workflows,
            "running_workflows_count": running_workflows,
            "status": "degraded" if failed_workflows > 0 else "healthy",
        }

    def retry_failed_workflow(
        self,
        session: Session,
        support_user_id: int,
        organization_id: int,
        workflow_id: int,
    ) -> Workflow:
        """Retries a failed workflow on behalf of the customer."""
        self._require_authorized_session(support_user_id, organization_id)

        wf = session.get(Workflow, workflow_id)
        if not wf or wf.organization_id != organization_id:
            raise ValidationError(f"Workflow ID {workflow_id} not found for organization {organization_id}")

        if wf.status != "failed":
            raise ValidationError(f"Cannot retry workflow with status '{wf.status}', must be 'failed'")

        wf.status = "pending"

        # Re-queue failed jobs
        session.query(Job).filter(Job.workflow_id == workflow_id, Job.status == "failed").update({"status": "pending"})

        audit = AuditEvent(
            action="support.workflow_retried",
            actor_id=support_user_id,
            organization_id=organization_id,
            details={"workflow_id": workflow_id},
        )
        session.add(audit)
        session.commit()
        session.refresh(wf)
        return wf

    def initiate_export(
        self,
        session: Session,
        support_user_id: int,
        organization_id: int,
    ) -> Dict[str, Any]:
        """Triggers a compliance data export package under support break-glass."""
        self._require_authorized_session(support_user_id, organization_id)
        return DisasterRecoveryService.export_tenant_data(session, organization_id)
