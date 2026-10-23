# webhook_server.py – Simple Flask server for GitHub App events
"""Entry point that receives GitHub webhook payloads, validates the HMAC
signature, transforms the event into a minimal job description and pushes it
onto the Redis queue consumed by ``gossipmesh_agent.queue_worker``.

The server is deliberately lightweight – it runs on Render (or any other
container host) and does not need any privileged Docker access. All heavy
lifting is delegated to the worker processes.
"""

import json
import os
import sys
from pathlib import Path

from flask import Flask, request, abort

# Import internal utilities – the package lives in the repository root.
# The repository root is added to ``sys.path`` by the Flask runner.
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from gossipmesh_agent import utils, ingestion
from gossipmesh_agent.queue_worker import REDIS_URL, redis_client, JOB_QUEUE, HEARTBEAT_PREFIX, CANCEL_PREFIX

app = Flask(__name__)

# Load optional .env for local development (Render supplies env vars via its UI)
utils.load_dotenv()
GITHUB_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")


@app.route("/cancel/<job_id>", methods=["POST"])
def cancel_job(job_id: str):
    """Endpoint to cancel a running job.
    Sets the Redis cancel flag for the given job id.
    Returns 200 if flag set, 404 if job not found in Redis.
    """
    # Simple existence check – if a heartbeat exists we consider it active.
    key = f"{HEARTBEAT_PREFIX}{job_id}"
    if not redis_client.exists(key):
        return {"status": "not_found", "job_id": job_id}, 404
    redis_client.set(f"{CANCEL_PREFIX}{job_id}", "true")
    return {"status": "cancelled", "job_id": job_id}, 200


def verify_signature(headers: dict, payload: bytes) -> bool:
    """Validate the ``X-Hub-Signature-256`` header using the shared secret.
    Returns ``True`` if the signature matches or the secret is missing (fallback for
    local debugging)."""
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
    # Raw body for HMAC verification
    raw_body = request.get_data()
    if not verify_signature(request.headers, raw_body):
        utils.logger.warning("Invalid webhook signature")
        abort(400, "Invalid signature")

    event = request.headers.get("X-GitHub-Event")
    if not event:
        abort(400, "Missing X-GitHub-Event header")

    payload = request.get_json(silent=True) or {}
    job = ingestion.handle_github_event(event, payload)
    # Attach a simple ID for tracing – we reuse the slug function.
    job_id = utils.slugify(json.dumps(job)[:80])
    job["id"] = job_id
    # Push onto Redis list (LPUSH for ordering, BLPOP in worker reads from the tail)
    redis_client.rpush(JOB_QUEUE, json.dumps(job))
    utils.logger.info("Enqueued job %s of type %s", job_id, job.get("type"))
    return {"status": "queued", "job_id": job_id}, 202


if __name__ == "__main__":
    # Render expects the server to bind to $PORT, default to 8080 for local dev.
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
