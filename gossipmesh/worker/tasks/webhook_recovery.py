from celery import shared_task
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from gossipmesh.worker.celery_app import celery_app
from gossipmesh.models.webhooks import WebhookEvent
from gossipmesh.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from gossipmesh.worker.tasks.webhook_dispatch import process_webhook_event

logger = logging.getLogger(__name__)
engine = create_engine(str(settings.DATABASE_URI))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@celery_app.task
def recover_stuck_webhooks():
    db: Session = SessionLocal()
    try:
        # Recover webhooks stuck in processing for more than 1 hour
        threshold = datetime.utcnow() - timedelta(hours=1)
        stuck_events = (
            db.query(WebhookEvent)
            .filter(WebhookEvent.status == "processing", WebhookEvent.created_at <= threshold)
            .all()
        )

        for event in stuck_events:
            logger.info(f"Recovering stuck webhook event {event.id}")
            event.status = "pending"
            db.commit()
            process_webhook_event.apply_async(args=[event.id])

    except Exception as e:
        logger.error(f"Failed to recover stuck webhooks: {e}")
    finally:
        db.close()
