from __future__ import annotations

import json
import logging
import hmac
import hashlib
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gossipmesh.core.config import settings
from gossipmesh.models.base import Base
from gossipmesh.models.billing import ProcessedWebhookEvent
from gossipmesh.observability.tracing import trace_webhook

logger = logging.getLogger(__name__)

engine = create_engine(str(settings.DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def process_webhook_event(event_id: str, payload: dict, signature: str, secret: str, destination_url: str) -> bool:
    with trace_webhook("stripe", payload.get("type", "unknown")):
        session = SessionLocal()
        try:
            existing = session.query(ProcessedWebhookEvent).filter_by(stripe_event_id=event_id).first()
            if existing:
                logger.info(f"Webhook event {event_id} already processed. Skipping.")
                return True

            payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
            expected_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_sig, signature):
                logger.warning(f"Invalid webhook signature for event {event_id}")
                return False

            # Process webhook event logic...
            record = ProcessedWebhookEvent(stripe_event_id=event_id, event_type=payload.get("type", "unknown"))
            session.add(record)
            session.commit()

            if destination_url:
                try:
                    with httpx.Client(timeout=10.0) as client:
                        client.post(
                            destination_url,
                            json=payload,
                            headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
                        )
                except Exception as ex:
                    logger.error(f"Failed to dispatch webhook to destination URL: {ex}")

            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error processing webhook {event_id}: {e}")
            return False
        finally:
            session.close()
