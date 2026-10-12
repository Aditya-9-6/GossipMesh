from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
import logging
import hashlib
import hmac
import os
import json

from gossipmesh.workflows.pr_review import PRReviewWorkflow
from gossipmesh.workflows.issue_solver import IssueSolverWorkflow
from gossipmesh.workflows.ci_fixer import CIFixerWorkflow

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
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle incoming GitHub webhooks for Milestone 6 and 7.
    Supported events: pull_request, issues, issue_comment, workflow_run
    """
    event = request.headers.get("X-GitHub-Event")
    if not event:
        raise HTTPException(
            status_code=400, detail="Missing X-GitHub-Event header"
        )

    payload_bytes = await request.body()
    if not verify_github_signature(request, payload_bytes):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(payload_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info(f"Received GitHub webhook event: {event}")

    # Milestone 6: PR Review
    if event == "pull_request":
        action = payload.get("action")
        if action in ["opened", "synchronize", "reopened"]:
            pr_data = payload.get("pull_request", {})
            workflow = PRReviewWorkflow(pr_data)
            background_tasks.add_task(workflow.execute)

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
