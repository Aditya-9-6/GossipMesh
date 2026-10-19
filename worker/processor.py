import json
import os
import subprocess
import sys
from pathlib import Path

# Path to the repository root (mounted in container)
REPO_ROOT = Path(os.getenv("REPO_ROOT", ".")).resolve()

def run_ai_reviewer(pr_number: int):
    """Invoke the existing ai_pr_reviewer script for a given PR number.
    Returns the JSON status file content.
    """
    script_path = REPO_ROOT / "scripts" / "ai_pr_reviewer.py"
    if not script_path.exists():
        raise FileNotFoundError(f"ai_pr_reviewer.py not found at {script_path}")
    env = os.environ.copy()
    # Ensure workspace is the repo root
    env["PYTHONPATH"] = str(REPO_ROOT / "scripts")
    # Use the same environment as the script expects (e.g., GH_TOKEN, keys)
    result = subprocess.run(
        [sys.executable, str(script_path), "--pr-number", str(pr_number), "--workspace", str(REPO_ROOT)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        print(f"[WARN] ai_pr_reviewer failed for PR #{pr_number}: {result.stderr}", file=sys.stderr)
        return None
    # The script writes status to ai_review_status.json
    status_file = REPO_ROOT / "ai_review_status.json"
    if status_file.exists():
        return json.loads(status_file.read_text())
    return None

def process_pr_event(payload: bytes):
    """RQ worker entry point. Parses a GitHub webhook payload and triggers review.
    Supports pull_request events (opened, reopened, synchronize).
    """
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        print("[ERROR] Invalid JSON payload", file=sys.stderr)
        return
    # Determine event type via headers is not available here, so inspect keys
    # For PR events, payload contains "pull_request" key
    pr = event.get("pull_request")
    if not pr:
        # Not a PR event – ignore (could extend to issues later)
        print("[INFO] Non-PR event received, ignoring.")
        return
    action = pr.get("action") or event.get("action")
    pr_number = pr.get("number") or event.get("number")
    if action not in {"opened", "reopened", "synchronize"}:
        print(f"[INFO] PR #{pr_number} action '{action}' not handled.")
        return
    print(f"[INFO] Processing PR #{pr_number} (action={action})")
    status = run_ai_reviewer(pr_number)
    if status:
        print(f"[RESULT] PR #{pr_number} review completed: {status['verdict']} (score {status['score']})")
    else:
        print(f"[WARN] No status returned for PR #{pr_number}")
