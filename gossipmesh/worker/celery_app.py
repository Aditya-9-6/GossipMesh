from celery import Celery  # type: ignore
from gossipmesh.core.config import settings

celery_app = Celery("worker", broker=settings.REDIS_URI, backend=settings.REDIS_URI)

celery_app.conf.task_routes = {"gossipmesh.worker.tasks.*": "main-queue"}


# Example task
@celery_app.task
def test_celery(word: str) -> str:
    return f"test task return {word}"
