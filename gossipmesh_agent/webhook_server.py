import os
import sys
import json
import hmac
import hashlib
import logging
from pathlib import Path
from flask import Flask, request, jsonify, abort

# Import internal utilities – the package lives in the repository root.
# The repository root is added to ``sys.path`` by the Flask runner.
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from gossipmesh_agent import utils, ingestion
from gossipmesh_agent.queue_worker import REDIS_URL, redis_client, JOB_QUEUE, HEARTBEAT_PREFIX, CANCEL_PREFIX

GITHUB_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
GITHUB_WEBHOOK_SECRET = GITHUB_SECRET

app = Flask(__name__)

# Load optional .env for local development (Render supplies env vars via its UI)
if os.path.exists(".env"):
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

utils.load_dotenv()

logger = logging.getLogger("gossipmesh_agent.webhook")
logging.basicConfig(level=logging.INFO)


@app.route("/cancel/<job_id>", methods=["POST"])
def cancel_job(job_id: str):
    """Endpoint to cancel a running job.
    Sets the Redis cancel flag for the given job id.
    Returns 200 if flag set, 404 if job not found in Redis.
    """
    key = f"{HEARTBEAT_PREFIX}{job_id}"
    if not redis_client.exists(key):
        return {"status": "not_found", "job_id": job_id}, 404
    redis_client.set(f"{CANCEL_PREFIX}{job_id}", "true")
    return {"status": "cancelled", "job_id": job_id}, 200


def verify_signature(headers: dict, payload: bytes) -> bool:
    """Validate the ``X-Hub-Signature-256`` header using the shared secret.
    Returns ``True`` if the signature matches or the secret is missing (fallback for
    local debugging)."""
    secret = GITHUB_SECRET or GITHUB_WEBHOOK_SECRET
    if not secret:
        return True
    signature = headers.get("X-Hub-Signature-256")
    if not signature:
        return False
    if "=" in signature:
        _, sig_hash = signature.split("=", 1)
    else:
        sig_hash = signature
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), sig_hash)


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok", "service": "gossipmesh-agent-webhook"}), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    raw_body = request.get_data()
    if not verify_signature(request.headers, raw_body):
        utils.logger.warning("Invalid webhook signature")
        return jsonify({"error": "Invalid signature"}), 401

    event_type = request.headers.get("X-GitHub-Event", "ping")
    payload = request.get_json(silent=True) or {}

    try:
        job = ingestion.handle_github_event(event_type, payload)
        job_id = utils.slugify(json.dumps(job)[:80])
        job["id"] = job_id
        
        if redis_client:
            redis_client.rpush(JOB_QUEUE, json.dumps(job))
            utils.logger.info("Enqueued job %s of type %s to Redis queue %s", job_id, event_type, JOB_QUEUE)
        else:
            utils.logger.error("Redis client not configured; cannot enqueue job.")
            return jsonify({"error": "Queue unavailable"}), 500
    except Exception as e:
        utils.logger.exception(f"Failed to enqueue webhook event: {e}")
        return jsonify({"error": "Internal error enqueuing job"}), 500

    return jsonify({"status": "queued", "job_id": job_id, "event": event_type}), 202


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
