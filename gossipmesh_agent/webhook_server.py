import os
import json
import hmac
import hashlib
import logging
from flask import Flask, request, jsonify
from gossipmesh_agent.queue_worker import REDIS_URL, redis_client, JOB_QUEUE

app = Flask(__name__)

# Load optional .env for local development (Render supplies env vars via its UI)
if os.path.exists(".env"):
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

logger = logging.getLogger("gossipmesh_agent.webhook")
logging.basicConfig(level=logging.INFO)

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


def verify_github_signature(req):
    if not GITHUB_WEBHOOK_SECRET:
        return True
    signature = req.headers.get("X-Hub-Signature-256")
    if not signature:
        return False
    if "=" in signature:
        _, sig_hash = signature.split("=", 1)
    else:
        sig_hash = signature
    mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), msg=req.data, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), sig_hash)


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok", "service": "gossipmesh-agent-webhook"}), 200


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    if not verify_github_signature(request):
        logger.warning("Invalid GitHub Webhook signature received.")
        return jsonify({"error": "Invalid signature"}), 401

    event_type = request.headers.get("X-GitHub-Event", "ping")
    payload = request.json or {}

    job_payload = {
        "type": event_type,
        "payload": payload,
        "repo": payload.get("repository", {}).get("full_name", "unknown"),
        "sender": payload.get("sender", {}).get("login", "unknown"),
    }

    try:
        if redis_client:
            redis_client.rpush(JOB_QUEUE, json.dumps(job_payload))
            logger.info(f"Enqueued job type={event_type} to Redis queue {JOB_QUEUE}")
        else:
            logger.error("Redis client not configured; cannot enqueue job.")
            return jsonify({"error": "Queue unavailable"}), 500
    except Exception as e:
        logger.exception(f"Failed to enqueue webhook event: {e}")
        return jsonify({"error": "Internal error enqueuing job"}), 500

    return jsonify({"status": "accepted", "event": event_type}), 202


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
