import json
import os
import sys
import redis
import subprocess
from pathlib import Path

from .utils import logger, load_dotenv, slugify
from .pipelines import run_issue_discovery, run_pr_review, run_auto_fix

# Load environment (including .env for local dev)
load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL)

JOB_QUEUE = "gossipmesh:jobs"
CANCEL_PREFIX = "gossipmesh:cancel:"
HEARTBEAT_PREFIX = "gossipmesh:heartbeat:"


def _is_cancelled(job_id: str) -> bool:
    return redis_client.get(f"{CANCEL_PREFIX}{job_id}") == b"true"


def _mark_started(job_id: str) -> None:
    redis_client.setex(f"{HEARTBEAT_PREFIX}{job_id}", 300, "alive")


def _clear_job_state(job_id: str) -> None:
    redis_client.delete(f"{CANCEL_PREFIX}{job_id}")
    redis_client.delete(f"{HEARTBEAT_PREFIX}{job_id}")


def start_worker() -> None:
    """Continuously poll Redis for new jobs and process them.
    Each job originates from ``ingestion.handle_github_event``.
    """
    logger.info("Worker started – listening on %s", JOB_QUEUE)
    while True:
        item = redis_client.blpop(JOB_QUEUE, timeout=5)
        if not item:
            continue
        _, raw = item
        job = json.loads(raw)
        job_id = job.get("id") or slugify(json.dumps(job)[:80])
        logger.info("Picked up job %s – type %s", job_id, job.get("type"))
        if _is_cancelled(job_id):
            logger.info("Job %s cancelled before start – would refund credits", job_id)
            _clear_job_state(job_id)
            continue
        _mark_started(job_id)
        try:
            job_type = job.get("type")
            if job_type in ("issue_opened", "issue_scan"):
                result = run_issue_discovery(job)
            elif job_type in ("pr_opened", "pr_review"):
                result = run_pr_review(job)
            elif job_type in ("auto_fix", "fix_issue"):
                result = run_auto_fix(job)
            else:
                logger.warning("Unsupported job type %s", job_type)
                result = {"status": "unsupported"}
            logger.info("Job %s finished – %s", job_id, result.get("status"))
        except Exception as exc:
            logger.exception("Job %s crashed with error: %s", job_id, exc)
            # Automatic credit refund on unexpected crash
            repo = job.get("repo")
            task_type = (
                "issue_scan"
                if job.get("type") == "issue_opened"
                else ("pr_review" if job.get("type") == "pr_opened" else "auto_fix")
            )
            if repo:
                from .credit_manager import release_credits

                release_credits(repo, task_type)
                logger.info("Automatically refunded credits for crashed job %s on %s", job_id, repo)
        finally:
            _clear_job_state(job_id)


if __name__ == "__main__":
    start_worker()
