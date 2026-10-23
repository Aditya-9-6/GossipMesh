#!/usr/bin/env python3
"""Simple webhook receiver for GossipMesh autonomous engine.

Render (or any other hosting platform) can POST to this endpoint when a GitHub
event of interest occurs (e.g., a new issue, a push, or a schedule). The
handler validates the request (optional HMAC verification) and then launches the
autonomous loop in a background subprocess.

Usage (in Render service configuration)::
    gunicorn --bind 0.0.0.0:$PORT webhook_handler:app

Environment variables expected:
    GITHUB_WEBHOOK_SECRET  – secret used to verify the X‑GitHub‑Signature header
    WORKSPACE              – path to the repository root (defaults to current dir)
    WORKER_ID              – numeric id for this worker (default: 1)
    NUM_WORKERS            – total workers in the pool (default: 5)
    INTERVAL               – poll interval in seconds (default: 5)
    ITERATIONS             – how many cycles to run (default: 30)
    MAX_MINUTES            – maximum runtime in minutes (default: 180)

The script starts ``scripts/autonomous_loop.py`` with the same arguments used by
the CI workflow. It writes logs to stdout which Render captures.
"""

import os
import hmac
import hashlib
import subprocess
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """Validate GitHub HMAC signature (sha256).
    GitHub sends header ``X-Hub-Signature-256: sha256=...``.
    """
    mac = hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256)
    expected = f"sha256={mac.hexdigest()}"
    return hmac.compare_digest(expected, signature)


@app.post("/webhook")
async def handle(request: Request):
    # Read raw body for signature verification
    body = await request.body()
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if secret:
        sig = request.headers.get("X-Hub-Signature-256")
        if not sig or not verify_signature(body, sig, secret):
            raise HTTPException(status_code=400, detail="Invalid signature")
    # Launch the autonomous loop as a detached process
    workspace = os.getenv("WORKSPACE", ".")
    worker_id = os.getenv("WORKER_ID", "1")
    num_workers = os.getenv("NUM_WORKERS", "5")
    interval = os.getenv("INTERVAL", "5")
    iterations = os.getenv("ITERATIONS", "30")
    max_minutes = os.getenv("MAX_MINUTES", "180")
    cmd = [
        "python",
        "scripts/autonomous_loop.py",
        "--workspace",
        workspace,
        "--worker-id",
        worker_id,
        "--num-workers",
        num_workers,
        "--interval",
        interval,
        "--iterations",
        iterations,
        "--max-minutes",
        max_minutes,
    ]
    # ``creationflags`` makes the subprocess detached on Windows; on *nix the
    # ``start_new_session`` flag does the same. Here we rely on ``subprocess.Popen``
    # with ``close_fds=True`` which works cross‑platform for a background task.
    try:
        subprocess.Popen(cmd, cwd=workspace, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start autonomous loop: {e}")
    return {"status": "autonomous loop started"}


if __name__ == "__main__":
    # For local debugging: ``uvicorn webhook_handler:app --reload``
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
