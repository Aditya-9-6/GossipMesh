import json
import os
import sys
from pathlib import Path

from flask import Flask, request, abort

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from gossipmesh_agent import utils, ingestion
from gossipmesh_agent.queue_worker import (
    REDIS_URL,
    redis_client,
    JOB_QUEUE,
)

HEARTBEAT_PREFIX = "gossipmesh:heartbeat:"
CANCEL_PREFIX = "gossipmesh:cancel:"

app = Flask(__name__)

utils.load_dotenv()

GITHUB_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


@app.route("/cancel/<job_id>", methods=["POST"])
def cancel_job(job_id: str):
    key = f"{HEARTBEAT_PREFIX}{job_id}"
    if not redis_client.exists(key):
        return {"status": "not_found", "job_id": job_id}, 404
    redis_client.set(f"{CANCEL_PREFIX}{job_id}", "true")
    return {"status": "cancelled", "job_id": job_id}, 200


def verify_signature(headers: dict, payload: bytes) -> bool:
    if not GITHUB_SECRET:
        return True
    signature = headers.get("X-Hub-Signature-256")
    if not signature:
        return False
    import hmac, hashlib

    expected = "sha256=" + hmac.new(GITHUB_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.route("/webhook", methods=["POST"])
def webhook():
    raw_body = request.get_data()
    if not verify_signature(request.headers, raw_body):
        utils.logger.warning("Invalid webhook signature")
        abort(400, "Invalid signature")

    event = request.headers.get("X-GitHub-Event")
    if not event:
        abort(400, "Missing X-GitHub-Event header")

    payload = request.get_json(silent=True) or {}
    job = ingestion.handle_github_event(event, payload)
    job_id = utils.slugify(json.dumps(job)[:80])
    job["id"] = job_id
    redis_client.rpush(JOB_QUEUE, json.dumps(job))
    utils.logger.info("Enqueued job %s of type %s", job_id, job.get("type"))
    return {"status": "queued", "job_id": job_id}, 202


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
