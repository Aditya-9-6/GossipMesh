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
    # Ensure workspace is the repo root and pythonpath includes both repo root and scripts
    env["PYTHONPATH"] = f"{REPO_ROOT};{REPO_ROOT / 'scripts'}"
    result = subprocess.run(
        [sys.executable, str(script_path), "--pr-number", str(pr_number), "--workspace", str(REPO_ROOT)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        print(f"[WARN] ai_pr_reviewer failed for PR #{pr_number}: {result.stderr}", file=sys.stderr)
        return None
    # The script writes status to ai_review_status.json
    status_file = REPO_ROOT / "ai_review_status.json"
    if status_file.exists():
        try:
            return json.loads(status_file.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def run_autonomous_cycle():
    """Runs a single autonomous loop cycle to pick up issues, solve them, and merge PRs."""
    script_path = REPO_ROOT / "scripts" / "autonomous_loop.py"
    if not script_path.exists():
        print(f"[WARN] autonomous_loop.py not found at {script_path}", file=sys.stderr)
        return
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{REPO_ROOT};{REPO_ROOT / 'scripts'}"
    print("[INFO] Launching autonomous advancement loop cycle in background...")
    try:
        subprocess.run(
            [sys.executable, str(script_path), "--workspace", str(REPO_ROOT), "--once"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=1200,
        )
    except Exception as e:
        print(f"[ERROR] Autonomous loop execution error: {e}", file=sys.stderr)


def process_pr_event(payload: bytes):
    """Worker entry point. Parses a GitHub webhook payload and triggers autonomous actions.
    Supports pull_request events, issue events, and ping/push triggers.
    """
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        print("[ERROR] Invalid JSON payload", file=sys.stderr)
        return

    # 1. Pull Request Events
    pr = event.get("pull_request")
    if pr:
        action = event.get("action") or pr.get("action")
        pr_number = pr.get("number") or event.get("number")
        if action in {"opened", "reopened", "synchronize"}:
            print(f"[INFO] Processing PR #{pr_number} (action={action})")
            status = run_ai_reviewer(pr_number)
            if status:
                print(
                    f"[RESULT] PR #{pr_number} review completed: {status.get('verdict')} (score {status.get('score')})"
                )
                if status.get("verdict") == "APPROVED" and status.get("score", 0) >= 90:
                    try:
                        from scripts.auto_merge_pr import auto_merge_pr

                        auto_merge_pr(str(pr_number), REPO_ROOT)
                    except Exception as e:
                        print(f"[WARN] Auto-merge failed for PR #{pr_number}: {e}")
            else:
                print(f"[WARN] No status returned for PR #{pr_number}")
            return

    # 2. Issue Events
    issue = event.get("issue")
    if issue:
        action = issue.get("action")
        issue_number = issue.get("number")
        print(f"[INFO] Issue #{issue_number} event received: {action}. Triggering autonomous advancement loop.")
        run_autonomous_cycle()
        return

    # 3. Push or Ping or other events
    if "zen" in event or "hook_id" in event:
        print("[INFO] Webhook ping received successfully from GitHub!")
        return

    # Default fallback: trigger advancement cycle
    print("[INFO] General webhook event received. Triggering autonomous advancement cycle.")
    run_autonomous_cycle()
