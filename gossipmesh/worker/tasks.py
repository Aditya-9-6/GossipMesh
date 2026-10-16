from celery import Task
from gossipmesh.db.session import SessionLocal
from gossipmesh.models.jobs import BackgroundJob
import logging

logger = logging.getLogger(__name__)

class DurableJobTask(Task):
    abstract = True

    def before_start(self, task_id, args, kwargs):
        super().before_start(task_id, args, kwargs)
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.task_id == task_id).first()
            if job:
                job.status = "running"
                job.worker_identity = self.request.hostname
                db.commit()
        except Exception as e:
            logger.error(f"Error updating job {task_id} before_start: {e}")
            db.rollback()
        finally:
            db.close()

    def on_success(self, retval, task_id, args, kwargs):
        super().on_success(retval, task_id, args, kwargs)
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.task_id == task_id).first()
            if job:
                job.status = "success"
                job.result = retval
                db.commit()
        except Exception as e:
            logger.error(f"Error updating job {task_id} on_success: {e}")
            db.rollback()
        finally:
            db.close()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        super().on_failure(exc, task_id, args, kwargs, einfo)
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.task_id == task_id).first()
            if job:
                if self.request.retries >= self.max_retries:
                    job.status = "dead_letter"
                else:
                    job.status = "failed"
                job.error_message = str(exc)
                db.commit()
        except Exception as e:
            logger.error(f"Error updating job {task_id} on_failure: {e}")
            db.rollback()
        finally:
            db.close()

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        super().on_retry(exc, task_id, args, kwargs, einfo)
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.task_id == task_id).first()
            if job:
                job.status = "pending" # going back to queue
                job.retries = self.request.retries
                job.error_message = str(exc)
                db.commit()
        except Exception as e:
            logger.error(f"Error updating job {task_id} on_retry: {e}")
            db.rollback()
        finally:
            db.close()

from gossipmesh.worker.celery_app import celery_app
from gossipmesh.jobs.pr_review import PRReviewJob
from gossipmesh.workflows.issue_solver import IssueSolverWorkflow
from gossipmesh.workflows.ci_fixer import CIFixerWorkflow
from gossipmesh.repository.github import GitHubIntegration
import asyncio

def _run_async(coro):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If there's already a running loop, create a task (useful in tests sometimes)
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return asyncio.run(coro)

@celery_app.task(bind=True, base=DurableJobTask, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_pr_review(self, pr_data: dict):
    job = PRReviewJob(pr_data)
    _run_async(job.execute())
    return {"status": "success", "action": "pr_review"}

@celery_app.task(bind=True, base=DurableJobTask, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_issue_solver(self, issue_data: dict):
    workflow = IssueSolverWorkflow(issue_data)
    _run_async(workflow.execute())
    return {"status": "success", "action": "issue_solver"}

@celery_app.task(bind=True, base=DurableJobTask, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_ci_fixer(self, run_data: dict):
    workflow = CIFixerWorkflow(run_data)
    _run_async(workflow.execute())
    return {"status": "success", "action": "ci_fixer"}

@celery_app.task(bind=True, base=DurableJobTask, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def sync_repository_task(self, full_name: str, installation_id: int, org_id: int):
    # Mocking similar to the previous background task
    mock_rsa_key = "-----BEGIN RSA PRIVATE KEY-----\nMIIBOQIBAAJAVY6qupT3\n-----END RSA PRIVATE KEY-----"
    github = GitHubIntegration(app_id="12345", private_key=mock_rsa_key)
    logger.info(f"Syncing {full_name} for installation {installation_id}")
    return {"status": "success", "action": "sync_repository", "repo": full_name}
