from sqlalchemy.sql import func
from fastapi import APIRouter, Request, BackgroundTasks, Depends, HTTPException
import logging
import hashlib
import hmac
import os
import json
import uuid
from sqlalchemy.orm import Session
from gossipmesh.api import deps
from gossipmesh.models.user import User
from gossipmesh.models.webhooks import WebhookEvent
from gossipmesh.models.audit import AuditEvent
from gossipmesh.models.jobs import BackgroundJob

from gossipmesh.worker.tasks import process_pr_review, process_issue_solver, process_ci_fixer

from gossipmesh.core.exceptions import AuthenticationError, ValidationError, AuthorizationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
def verify_github_signature(request: Request, payload: bytes) -> bool:
    """
    Verify the signature of the incoming GitHub webhook payload.
    """
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    if not secret:
        # If secret is not configured, we allow it for development only
        if os.environ.get("ENVIRONMENT") == "development":
            logger.warning(
                "GITHUB_WEBHOOK_SECRET is not set, skipping signature verification in development"
            )
            return True
        else:
            logger.error("GITHUB_WEBHOOK_SECRET is not set in a non-development environment")
            return False

    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        logger.error("Missing X-Hub-Signature-256 header")
        return False

    hash_object = hmac.new(
        secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()

    if not hmac.compare_digest(expected_signature, signature_header):
        logger.error("Signature verification failed")
        return False

    return True



def dispatch_webhook(event: str, payload: dict, db: Session):
    task_id = str(uuid.uuid4())

    if event == "pull_request":
        action = payload.get("action")
        if action in ["opened", "synchronize", "reopened"]:
            pr_data = payload.get("pull_request", {})

            job_record = BackgroundJob(task_id=task_id, task_name="process_pr_review")
            db.add(job_record)
            db.commit()

            process_pr_review.apply_async(args=[pr_data], task_id=task_id)

    # Milestone 7: Issue Solver
    elif event == "issues":
        action = payload.get("action")
        if action == "opened":
            issue_data = payload.get("issue", {})

            job_record = BackgroundJob(task_id=task_id, task_name="process_issue_solver")
            db.add(job_record)
            db.commit()

            process_issue_solver.apply_async(args=[issue_data], task_id=task_id)

    # Milestone 7: CI Fixer (Triggered by workflow_run completion)
    elif event == "workflow_run":
        action = payload.get("action")
        run_data = payload.get("workflow_run", {})
        if action == "completed" and run_data.get("conclusion") == "failure":

            job_record = BackgroundJob(task_id=task_id, task_name="process_ci_fixer")
            db.add(job_record)
            db.commit()

            process_ci_fixer.apply_async(args=[run_data], task_id=task_id)

    elif event == "issue_comment":
        action = payload.get("action")
        if action == "created":
            # Handle human approval workflow or explicit commands
            comment_body = payload.get("comment", {}).get("body", "")
            if "/approve" in comment_body:
                logger.info("Human approval received via comment.")
                # Trigger approval state transition logic here

@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db)
):
    """
    Handle incoming GitHub webhooks for Milestone 6 and 7.
    Supported events: pull_request, issues, issue_comment, workflow_run
    """
    event = request.headers.get("X-GitHub-Event")
    if not event:
        raise ValidationError(message="Missing X-GitHub-Event header")

    delivery_id = request.headers.get("X-GitHub-Delivery")
    if not delivery_id:
        raise ValidationError(message="Missing X-GitHub-Delivery header")

    payload_bytes = await request.body()
    if not verify_github_signature(request, payload_bytes):
        raise AuthenticationError(message="Invalid signature")

    try:
        payload = json.loads(payload_bytes)
    except Exception:
        raise ValidationError(message="Invalid JSON payload")

    logger.info(f"Received GitHub webhook event: {event} with delivery_id: {delivery_id}")

    # Check for idempotency
    existing_event = db.query(WebhookEvent).filter(WebhookEvent.delivery_id == delivery_id).first()
    if existing_event:
        logger.info(f"Webhook {delivery_id} already processed. Skipping.")
        return {"status": "already_processed", "event": event}

    # Store event
    webhook_record = WebhookEvent(
        delivery_id=delivery_id,
        event=event,
        payload=payload,
        status="pending"
    )
    db.add(webhook_record)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise e

    try:
        dispatch_webhook(event, payload, db)
        webhook_record.status = "processed"
    except Exception as e:
        webhook_record.status = "failed"
        logger.error(f"Failed to dispatch webhook: {e}")
        db.commit()
        raise e

    db.commit()
    return {"status": "accepted", "event": event}

@router.post("/github/replay/{event_id}")
async def replay_github_webhook(
    event_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Administrator-only webhook replay mechanism.
    """
    if not current_user.is_superuser:
        raise AuthorizationError(message="Administrator privileges required")

    event_record = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
    if not event_record:
        raise HTTPException(status_code=404, detail="Webhook event not found")

    try:
        dispatch_webhook(event_record.event, event_record.payload, db)
        event_record.replayed_at = func.now()
        event_record.replayed_by = current_user.id

        # Log AuditEvent
        audit = AuditEvent(
            action="webhook.replayed",
            actor_id=current_user.id,
            details={"event_id": event_id, "delivery_id": event_record.delivery_id}
        )
        db.add(audit)
        db.commit()
        return {"status": "replayed", "event": event_record.event}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to replay webhook {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to replay webhook")
