import os
import json
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from rq import Queue
from redis import Redis
from worker.processor import process_pr_event

app = FastAPI()

# Initialize Redis connection and queue
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = Redis.from_url(redis_url)
q = Queue('github-events', connection=redis_conn)

# Load GitHub webhook secret
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
if not WEBHOOK_SECRET:
    raise RuntimeError("GITHUB_WEBHOOK_SECRET environment variable not set")

class GitHubEvent(BaseModel):
    action: str = None
    number: int = None
    pull_request: dict = None
    repository: dict = None

def verify_signature(request: Request, payload: bytes):
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        raise HTTPException(status_code=400, detail='Missing signature')
    sha_name, signature = signature.split('=')
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
    # Enqueue processing (the worker will handle PR logic)
    q.enqueue(process_pr_event, payload)
    return {"status": "queued"}
