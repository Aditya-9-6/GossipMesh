"""
Distributed Worker Lease and Heartbeat Manager (Task 79).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, and_
from sqlalchemy.orm import Session

from gossipmesh.models.runtime import Job
from gossipmesh.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class WorkerLeaseManager:
    """Manages distributed worker job leases, heartbeats, and stale re-queuing."""

    def __init__(self, lease_duration_seconds: int = 60, heartbeat_timeout_seconds: int = 30):
        self.lease_duration_seconds = lease_duration_seconds
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds

    def acquire_job_lease(
        self,
        session: Session,
        worker_id: str,
        job_type: Optional[str] = None,
    ) -> Optional[Job]:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.lease_duration_seconds)

        stmt = (
            select(Job)
            .where(
                and_(
                    Job.status == "pending",
                    (Job.lease_expires_at == None) | (Job.lease_expires_at < now),
                )
            )
            .order_by(Job.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job_type:
            stmt = stmt.where(Job.job_type == job_type)

        job = session.execute(stmt).scalars().first()
        if not job:
            return None

        job.worker_id = worker_id
        job.lease_token = f"lease_{worker_id}_{int(now.timestamp())}"
        job.heartbeat_at = now
        job.lease_expires_at = expires_at
        job.attempts = (job.attempts or 0) + 1
        job.status = "running"

        session.commit()
        session.refresh(job)
        return job

    def send_heartbeat(
        self,
        session: Session,
        job_id: int,
        worker_id: str,
        lease_token: str,
    ) -> bool:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.lease_duration_seconds)

        stmt = select(Job).where(
            and_(
                Job.id == job_id,
                Job.worker_id == worker_id,
                Job.lease_token == lease_token,
                Job.status == "running",
            )
        )
        job = session.execute(stmt).scalars().first()
        if not job:
            return False

        job.heartbeat_at = now
        job.lease_expires_at = expires_at
        session.commit()
        return True

    def release_job(
        self,
        session: Session,
        job_id: int,
        worker_id: str,
        lease_token: str,
        success: bool = True,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        stmt = select(Job).where(
            and_(
                Job.id == job_id,
                Job.worker_id == worker_id,
                Job.lease_token == lease_token,
            )
        )
        job = session.execute(stmt).scalars().first()
        if not job:
            return False

        if success:
            job.status = "completed"
            job.result_data = result_data or {}
        else:
            job.status = "failed"
            job.error_message = error_message or "Unknown failure"

        job.lease_token = None
        job.lease_expires_at = None
        session.commit()
        return True

    def renew_lease(
        self,
        session: Session,
        job_id: int,
        worker_id: str,
        lease_token: str,
    ) -> Optional[datetime]:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.lease_duration_seconds)

        stmt = select(Job).where(
            and_(
                Job.id == job_id,
                Job.worker_id == worker_id,
                Job.lease_token == lease_token,
                Job.status == "running",
            )
        )
        job = session.execute(stmt).scalars().first()
        if not job:
            return None

        job.heartbeat_at = now
        job.lease_expires_at = expires_at
        session.commit()
        return expires_at

    def reclaim_stale_leases(self, session: Session) -> int:
        now = datetime.now(timezone.utc)
        stmt = select(Job).where(
            and_(
                Job.status == "running",
                Job.lease_expires_at != None,
                Job.lease_expires_at < now,
            )
        )
        stale_jobs = session.execute(stmt).scalars().all()
        reclaimed_count = 0

        for job in stale_jobs:
            if (job.attempts or 0) >= 3:
                job.status = "failed"
                job.error_message = "Max retry attempts exceeded via stale lease reclaim"
            else:
                job.status = "pending"

            job.worker_id = None
            job.lease_token = None
            job.lease_expires_at = None
            reclaimed_count += 1

        if reclaimed_count > 0:
            session.commit()

        return reclaimed_count
