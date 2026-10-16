from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.organization import UserOrganization
from gossipmesh.models.jobs import BackgroundJob
from gossipmesh.core.exceptions import AuthorizationError
from gossipmesh.worker.celery_app import celery_app

router = APIRouter()

@router.get("/{task_id}")
def get_job_status(
    task_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    job = db.query(BackgroundJob).filter(BackgroundJob.task_id == task_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # If job has organization_id, enforce org membership
    if job.organization_id:
        is_member = db.query(UserOrganization).filter(
            UserOrganization.user_id == current_user.id,
            UserOrganization.organization_id == job.organization_id
        ).first()
        if not is_member and job.user_id != current_user.id and not current_user.is_superuser:
            raise AuthorizationError(message="Not authorized to access this job")
    elif job.user_id != current_user.id and not current_user.is_superuser:
        raise AuthorizationError(message="Not authorized to access this job")

    return {
        "task_id": job.task_id,
        "task_name": job.task_name,
        "status": job.status,
        "result": job.result,
        "error_message": job.error_message,
        "retries": job.retries,
        "worker_identity": job.worker_identity,
        "created_at": job.created_at
    }

@router.post("/{task_id}/cancel")
def cancel_job(
    task_id: str,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
) -> Any:
    job = db.query(BackgroundJob).filter(BackgroundJob.task_id == task_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.organization_id:
        is_member = db.query(UserOrganization).filter(
            UserOrganization.user_id == current_user.id,
            UserOrganization.organization_id == job.organization_id
        ).first()
        if not is_member and job.user_id != current_user.id and not current_user.is_superuser:
            raise AuthorizationError(message="Not authorized to access this job")
    elif job.user_id != current_user.id and not current_user.is_superuser:
        raise AuthorizationError(message="Not authorized to access this job")

    if job.status in ["success", "failed", "dead_letter", "cancelled"]:
        raise HTTPException(status_code=400, detail="Cannot cancel a completed job")

    # Cancel in celery
    celery_app.control.revoke(task_id, terminate=True)

    job.status = "cancelled"
    db.commit()

    return {"status": "cancelled", "task_id": task_id}
