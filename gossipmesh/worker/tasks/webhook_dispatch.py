import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.worker.celery_app import celery_app
from gossipmesh.models.webhooks import WebhookEvent
from gossipmesh.core.config import settings
from gossipmesh.core.concurrency_limit import ConcurrencyLimiter
from gossipmesh.core.exceptions import ConcurrencyLimitError

from gossipmesh.jobs.pr_review import PRReviewJob
from gossipmesh.workflows.issue_solver import IssueSolverWorkflow
from gossipmesh.workflows.ci_fixer import CIFixerWorkflow

logger = logging.getLogger(__name__)

engine = create_engine(str(settings.DATABASE_URI))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

MAX_RETRIES = 5


async def async_dispatch(event: str, payload: Dict[str, Any], db: Session | None = None):
    if event == "pull_request":
        action = payload.get("action")
        if action in ["opened", "synchronize", "reopened"]:
            pr_data = payload.get("pull_request", {})
            job = PRReviewJob(pr_data, workflow_id=1, db=db)
            await job.execute()

    elif event == "issues":
        action = payload.get("action")
        if action == "opened":
            issue_data = payload.get("issue", {})
            workflow = IssueSolverWorkflow(issue_data)
            await workflow.execute()

    elif event == "workflow_run":
        action = payload.get("action")
        run_data = payload.get("workflow_run", {})
        if action == "completed" and run_data.get("conclusion") == "failure":
            ci_workflow = CIFixerWorkflow(run_data)
            await ci_workflow.execute()

    elif event == "issue_comment":
        action = payload.get("action")
        if action == "created":
            comment_body = payload.get("comment", {}).get("body", "")
            if "/approve" in comment_body:
                logger.info("Human approval received via comment.")


@celery_app.task(bind=True, max_retries=MAX_RETRIES)
def process_webhook_event(self, webhook_event_id: int):
    db: Session = SessionLocal()
    try:
        webhook_record = db.query(WebhookEvent).filter(WebhookEvent.id == webhook_event_id).first()
        if not webhook_record:
            logger.error(f"WebhookEvent {webhook_event_id} not found.")
            return

        webhook_record.status = "processing"
        db.commit()

        try:
<<<<<<< HEAD
            payload = webhook_record.payload or {}
            org_id = None

            # Robust payload parsing
            if payload and isinstance(payload, dict):
                org = payload.get("organization")
                if org and isinstance(org, dict) and "id" in org:
                    org_id = str(org["id"])
                else:
                    repo = payload.get("repository")
                    if repo and isinstance(repo, dict):
                        owner = repo.get("owner")
                        if owner and isinstance(owner, dict) and "id" in owner:
                            org_id = str(owner["id"])

            if not org_id:
                org_id = "default_tenant"

            # 5 active operations per organization limit
            limiter = ConcurrencyLimiter(limit=5)

            with limiter.limit_concurrency(identifier=org_id, operation_type="webhook_dispatch"):
                asyncio.run(async_dispatch(webhook_record.event, webhook_record.payload))
=======
            asyncio.run(async_dispatch(webhook_record.event, webhook_record.payload, db=db))
>>>>>>> origin/main

            webhook_record.status = "processed"
            db.commit()

        except ConcurrencyLimitError as e:
            logger.warning(f"Concurrency limit exceeded for webhook {webhook_event_id}, retrying...")
            # We want to retry faster since this is just a limit, maybe exponential backoff still applies
            webhook_record.retries += 1
            if webhook_record.retries >= MAX_RETRIES:
                webhook_record.status = "dead_letter"
            else:
                webhook_record.status = "failed"
                delay = 2**webhook_record.retries
                webhook_record.next_retry_at = datetime.utcnow() + timedelta(minutes=delay)
            db.commit()

            if webhook_record.retries < MAX_RETRIES:
                raise self.retry(exc=e, countdown=delay * 60)

        except Exception as e:
            logger.error(f"Failed to process webhook {webhook_event_id}: {e}")

            webhook_record.retries += 1
            if webhook_record.retries >= MAX_RETRIES:
                webhook_record.status = "dead_letter"
            else:
                webhook_record.status = "failed"
                delay = 2**webhook_record.retries
                webhook_record.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=delay)

            db.commit()

            if webhook_record.retries < MAX_RETRIES:
                raise self.retry(exc=e, countdown=delay * 60)

    finally:
        db.close()
