from celery import Celery  # type: ignore
from gossipmesh.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URI,
    backend=settings.REDIS_URI
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_transport_options={'visibility_timeout': 3600},
    task_routes={
        "gossipmesh.worker.tasks.*": "main-queue"
    }
)

# Includes for tasks
celery_app.conf.imports = (
    "gossipmesh.worker.tasks",
)
