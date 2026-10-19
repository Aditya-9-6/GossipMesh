import os
import json
import hmac
import hashlib
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from worker.processor import process_pr_event

app = FastAPI()
thread_pool = ThreadPoolExecutor(max_workers=5)

# Initialize Redis connection and queue (optional fallback to in-memory/thread)
redis_url = os.getenv("REDIS_URL")
q = None
if redis_url:
    try:
        from redis import Redis
        from rq import Queue
        redis_conn = Redis.from_url(redis_url)
        q = Queue('github-events', connection=redis_conn)
    except Exception as e:
        print(f"[WARN] Redis unavailable ({e}), falling back to direct background thread processing.")

# Load GitHub webhook secret
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

class GitHubEvent(BaseModel):
    action: str = None
    number: int = None
    pull_request: dict = None
    repository: dict = None

@app.get("/")
@app.get("/healthz")
async def health():
    return {"status": "ok", "service": "GossipMesh Autonomous Reviewer"}

def verify_signature(request: Request, payload: bytes):
    if not WEBHOOK_SECRET:
        return
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        raise HTTPException(status_code=400, detail='Missing signature')
    if '=' in signature:
        sha_name, signature = signature.split('=', 1)
    mac = hmac.new(WEBHOOK_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
    if not hmac.compare_digest(mac.hexdigest(), signature):
        raise HTTPException(status_code=400, detail='Invalid signature')

@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.body()
    verify_signature(request, payload)
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail='Invalid JSON')

    # Dispatch via Redis if configured, otherwise run directly in background thread pool
    if q is not None:
        try:
            q.enqueue(process_pr_event, payload)
            return {"status": "queued_redis"}
        except Exception as e:
            print(f"[WARN] Failed to enqueue to Redis ({e}), using thread pool fallback.")

    loop = asyncio.get_event_loop()
    loop.run_in_executor(thread_pool, process_pr_event, payload)
    return {"status": "queued_async"}

# Diagnostics endpoint to expose worker count
@app.get("/debug/worker_status")
def worker_status():
    """Return the configured number of worker threads handling PR events."""
    return {"active_workers": thread_pool._max_workers}

# Ready endpoint for Kubernetes liveness/readiness probes
@app.get("/ready")
async def ready():
    # Simple readiness check – could be expanded to DB connections, etc.
    return {"status": "ready", "service": "GossipMesh Autonomous Reviewer"}
