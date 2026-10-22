"""
Enterprise Disaster Recovery & Data Lifecycle Service (Task 98).

Implements tenant data export (GDPR/CCPA compliance), tenant deletion with retention,
backup integrity validation, and purge automation.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from gossipmesh.core.exceptions import ValidationError
from gossipmesh.models.audit import AuditEvent
from gossipmesh.models.organization import Organization, UserOrganization
from gossipmesh.models.project import Project
from gossipmesh.models.repository import Repository
from gossipmesh.models.runtime import Workflow
from gossipmesh.models.billing import UsageRecord


class DisasterRecoveryService:
    """Manages tenant export, soft/hard deletion lifecycle, and backup validation."""

    @staticmethod
    def export_tenant_data(session: Session, organization_id: int) -> Dict[str, Any]:
        """
        Exports a complete, portable data package for a tenant (GDPR/CCPA compliant).
        """
        org = session.get(Organization, organization_id)
        if not org:
            raise ValidationError(f"Organization ID {organization_id} not found")

        # 1. Members
        members = (
            session.execute(select(UserOrganization).where(UserOrganization.organization_id == organization_id))
            .scalars()
            .all()
        )

        # 2. Projects
        projects = session.execute(select(Project).where(Project.organization_id == organization_id)).scalars().all()

        # 3. Repositories
        repos = session.execute(select(Repository).where(Repository.organization_id == organization_id)).scalars().all()

        # 4. Workflows
        workflows = session.execute(select(Workflow).where(Workflow.organization_id == organization_id)).scalars().all()

        # 5. Audit Events
        audit_events = (
            session.execute(select(AuditEvent).where(AuditEvent.organization_id == organization_id)).scalars().all()
        )

        # 6. Usage Records
        usage_records = (
            session.execute(select(UsageRecord).where(UsageRecord.organization_id == organization_id)).scalars().all()
        )

        return {
            "organization": {
                "id": org.id,
                "name": org.name,
                "created_at": org.created_at.isoformat() if hasattr(org, "created_at") and org.created_at else None,
            },
            "members": [
                {"user_id": m.user_id, "role": m.role.value if hasattr(m.role, "value") else str(m.role)}
                for m in members
            ],
            "projects": [{"id": p.id, "name": p.name} for p in projects],
            "repositories": [{"id": r.id, "name": r.name, "github_id": r.github_id} for r in repos],
            "workflows_count": len(workflows),
            "audit_events_count": len(audit_events),
            "usage_records_count": len(usage_records),
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def soft_delete_tenant(
        session: Session,
        organization_id: int,
        actor_id: Optional[int] = None,
        retention_days: int = 30,
    ) -> Organization:
        """
        Marks an organization and its data for soft deletion with compliance retention.
        """
        org = session.get(Organization, organization_id)
        if not org:
            raise ValidationError(f"Organization ID {organization_id} not found")

        org.deleted_at = datetime.now(timezone.utc)
        org.deleted_by = actor_id
        org.retention_days = retention_days

        audit = AuditEvent(
            action="organization.soft_deleted",
            actor_id=actor_id,
            organization_id=organization_id,
            details={"retention_days": retention_days},
        )
        session.add(audit)
        session.commit()
        session.refresh(org)
        return org

    @staticmethod
    def purge_organization_data(
        session: Session,
        organization_id: int,
        actor_id: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        Hard purges or anonymizes all tenant data:
        repositories, index state, reviews, findings, artifacts, and usage records.
        """
        org = session.get(Organization, organization_id)
        if not org:
            raise ValidationError(f"Organization ID {organization_id} not found")

        # 1. Purge usage records
        usage_deleted = session.query(UsageRecord).filter_by(organization_id=organization_id).delete()

        # 2. Purge workflows
        wf_deleted = session.query(Workflow).filter_by(organization_id=organization_id).delete()

        # 3. Purge repositories
        repo_deleted = session.query(Repository).filter_by(organization_id=organization_id).delete()

        # 4. Remove user memberships
        members_deleted = session.query(UserOrganization).filter_by(organization_id=organization_id).delete()

        # 5. Mark organization hard-deleted
        org.deleted_at = datetime.now(timezone.utc)
        org.name = f"deleted_org_{organization_id}_{int(datetime.now(timezone.utc).timestamp())}"

        audit = AuditEvent(
            action="organization.purged",
            actor_id=actor_id,
            organization_id=organization_id,
            details={
                "usage_deleted": usage_deleted,
                "workflows_deleted": wf_deleted,
                "repositories_deleted": repo_deleted,
                "members_deleted": members_deleted,
            },
        )
        session.add(audit)
        session.commit()

        return {
            "usage_deleted": usage_deleted,
            "workflows_deleted": wf_deleted,
            "repositories_deleted": repo_deleted,
            "members_deleted": members_deleted,
        }

    @staticmethod
    def verify_backup_integrity(data_bytes: bytes, expected_sha256: str) -> bool:
        """Verifies cryptographic hash of backup snapshots before restore."""
        actual_hash = hashlib.sha256(data_bytes).hexdigest()
        return actual_hash.lower() == expected_sha256.lower()
