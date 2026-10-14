from fastapi import APIRouter, Request
from fastapi import BackgroundTasks
from fastapi import Depends
from sqlalchemy.orm import Session
import logging
import hashlib
import hmac
import os
import json

from gossipmesh.api import deps
from gossipmesh.jobs.pr_review import PRReviewJob
from gossipmesh.workflows.issue_solver import IssueSolverWorkflow
from gossipmesh.workflows.ci_fixer import CIFixerWorkflow
from gossipmesh.core.exceptions import AuthenticationError, ValidationError
from gossipmesh.models.repository import GithubAppInstallation
from gossipmesh.models.audit import AuditEvent

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


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db)
):
    """
    Handle incoming GitHub webhooks.
    Supported events: pull_request, issues, issue_comment, workflow_run, installation, installation_repositories
    """
    event = request.headers.get("X-GitHub-Event")
    if not event:
        raise ValidationError(message="Missing X-GitHub-Event header")

    payload_bytes = await request.body()
    if not verify_github_signature(request, payload_bytes):
        raise AuthenticationError(message="Invalid signature")

    try:
        payload = json.loads(payload_bytes)
    except Exception:
        raise ValidationError(message="Invalid JSON payload")

    logger.info(f"Received GitHub webhook event: {event}")

    if event == "installation":
        action = payload.get("action")
        installation_data = payload.get("installation", {})
        installation_id = installation_data.get("id")
        account = installation_data.get("account", {})

        if action == "created":
            installation = db.query(GithubAppInstallation).filter(GithubAppInstallation.installation_id == installation_id).first()
            if not installation:
                installation = GithubAppInstallation(
                    installation_id=installation_id,
                    account_name=account.get("login"),
                    target_type=account.get("type"),
                    target_id=account.get("id"),
                    repository_selection=installation_data.get("repository_selection", "all"),
                    permissions=installation_data.get("permissions", {})
                )
                db.add(installation)
                db.commit()

                audit = AuditEvent(
                    action="github_app_installation_created",
                    details={"installation_id": installation_id, "account": account.get("login")}
                )
                db.add(audit)
                db.commit()
            else:
                logger.info(f"Installation {installation_id} already exists, ignoring duplicate created event.")

        elif action == "deleted":
            installation = db.query(GithubAppInstallation).filter(GithubAppInstallation.installation_id == installation_id).first()
            if installation:
                db.delete(installation)
                db.commit()

                audit = AuditEvent(
                    action="github_app_installation_deleted",
                    details={"installation_id": installation_id, "account": account.get("login")}
                )
                db.add(audit)
                db.commit()

        elif action == "suspend":
            installation = db.query(GithubAppInstallation).filter(GithubAppInstallation.installation_id == installation_id).first()
            if installation:
                suspended_at_str = payload.get("installation", {}).get("suspended_at")
                if suspended_at_str:
                    from datetime import datetime
                    # replace Z with +00:00 for fromisoformat compatibility
                    installation.suspended_at = datetime.fromisoformat(suspended_at_str.replace("Z", "+00:00"))
                else:
                    installation.suspended_at = None
                installation.suspended_by = payload.get("installation", {}).get("suspended_by", {}).get("login")
                db.commit()

                audit = AuditEvent(
                    action="github_app_installation_suspended",
                    details={"installation_id": installation_id, "account": account.get("login")}
                )
                db.add(audit)
                db.commit()

        elif action == "unsuspend":
            installation = db.query(GithubAppInstallation).filter(GithubAppInstallation.installation_id == installation_id).first()
            if installation:
                installation.suspended_at = None
                installation.suspended_by = None
                db.commit()

                audit = AuditEvent(
                    action="github_app_installation_unsuspended",
                    details={"installation_id": installation_id, "account": account.get("login")}
                )
                db.add(audit)
                db.commit()

    elif event == "installation_repositories":
        action = payload.get("action")
        installation_data = payload.get("installation", {})
        installation_id = installation_data.get("id")

        if action in ["added", "removed"]:
            installation = db.query(GithubAppInstallation).filter(GithubAppInstallation.installation_id == installation_id).first()
            if installation:
                installation.repository_selection = installation_data.get("repository_selection", installation.repository_selection)
                db.commit()

                audit = AuditEvent(
                    action=f"github_app_installation_repositories_{action}",
                    details={
                        "installation_id": installation_id,
                        "repositories_added": [r.get("full_name") for r in payload.get("repositories_added", [])],
                        "repositories_removed": [r.get("full_name") for r in payload.get("repositories_removed", [])]
                    }
                )
                db.add(audit)
                db.commit()

    # Milestone 6: PR Review
    elif event == "pull_request":
        action = payload.get("action")
        if action in ["opened", "synchronize", "reopened"]:
            pr_data = payload.get("pull_request", {})
            job = PRReviewJob(pr_data)
            background_tasks.add_task(job.execute)

    # Milestone 7: Issue Solver
    elif event == "issues":
        action = payload.get("action")
        if action == "opened":
            issue_data = payload.get("issue", {})
            workflow = IssueSolverWorkflow(issue_data)
            background_tasks.add_task(workflow.execute)

    # Milestone 7: CI Fixer (Triggered by workflow_run completion)
    elif event == "workflow_run":
        action = payload.get("action")
        run_data = payload.get("workflow_run", {})
        if action == "completed" and run_data.get("conclusion") == "failure":
            workflow = CIFixerWorkflow(run_data)
            background_tasks.add_task(workflow.execute)

    elif event == "issue_comment":
        action = payload.get("action")
        if action == "created":
            # Handle human approval workflow or explicit commands
            comment_body = payload.get("comment", {}).get("body", "")
            if "/approve" in comment_body:
                logger.info("Human approval received via comment.")
                # Trigger approval state transition logic here

    return {"status": "accepted", "event": event}
