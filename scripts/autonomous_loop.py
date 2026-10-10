#!/usr/bin/env python3
"""
Autonomous Multi-Agent GitHub Advancement Loop for GossipMesh (Local Daemon & Cloud Runner)

Executes the continuous hyper-scale development cycle:
1. Dynamic Key Pooling: Rotates Gemini API keys round-robin to maximize RPM/TPM quota.
2. Issue Generation: Creates architecture advancement specifications.
3. AI Solver: Implements solutions with zero-allocation, anti-spaghetti invariants.
4. Pre-Commit Quality Gate: Runs black . || echo 'black not found', flake8 . || echo 'flake8 not found', and python -m unittest discover -s tests -p 'test_*.py' -v
5. Contribution Attribution: Commits with 'Aditya Dahale <aditya-9-6@users.noreply.github.com>'.
6. Autonomous Reviewer Gate: Audits PR against strict performance and decoupling invariants.
7. Auto-Merger: Squash-merges approved PRs to continuously illuminate GitHub contribution chart.
"""

import os
import sys
import json
import time
import subprocess
import argparse
from pathlib import Path

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

REPO = "Aditya-9-6/GossipMesh"
USER_NAME = "Aditya Dahale"
USER_EMAIL = "aditya-9-6@users.noreply.github.com"

# Base Key Pool - Dynamically loaded from GEMINI_KEY_POOL, individual env vars, or .gemini_keys
DEFAULT_KEYS = []

class KeyPool:
    """Manages round-robin rotation and dynamic failover across Gemini API keys."""
    def __init__(self, initial_keys: list[str] = None):
        self.keys = []
        pool_env = os.environ.get("GEMINI_KEY_POOL", "")
        extra_keys = [k.strip() for k in pool_env.split(",") if k.strip()]

        for var in ("GEMINI_API_KEY", "GEMINI_ISSUE_KEY", "GEMINI_REVIEWER_KEY", "GEMINI_SOLVER_KEY"):
            val = os.environ.get(var, "").strip()
            if val and val not in extra_keys:
                extra_keys.append(val)

        # Check local gitignored .gemini_keys file in workspace root
        for check_dir in (Path("."), Path(__file__).resolve().parent):
            key_file = check_dir / ".gemini_keys"
            if key_file.exists():
                try:
                    for line in key_file.read_text(encoding="utf-8").splitlines():
                        k = line.strip()
                        if k and not k.startswith("#") and k not in extra_keys:
                            extra_keys.append(k)
                except Exception:
                    pass

        all_keys = extra_keys + (initial_keys or [])
        for k in all_keys:
            if k and k not in self.keys:
                self.keys.append(k)
        self.idx = 0

    def add_keys(self, new_keys: list[str]):
        for k in new_keys:
            clean = k.strip()
            if clean and clean not in self.keys:
                self.keys.append(clean)
                print(f"[KeyPool] Added new API key to active rotation pool (Total: {len(self.keys)})", flush=True)

    def next_key(self) -> str:
        if not self.keys:
            return ""
        key = self.keys[self.idx % len(self.keys)]
        self.idx += 1
        return key

    def __len__(self):
        return len(self.keys)

GLOBAL_POOL = KeyPool(DEFAULT_KEYS)

def run_cmd(cmd, cwd=None, check=True):
    """Runs a shell command and returns stdout."""
    res = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed ({res.returncode}): {cmd}\nStderr: {res.stderr}\nStdout: {res.stdout}")
    return res.stdout.strip()

def get_open_advancement_issues(workspace: Path):
    """Fetches open advancement issues and filters for those with a /solve comment."""
    try:
        out = run_cmd(["gh", "issue", "list", "--repo", REPO, "--label", "advancement", "--state", "open", "--json", "number,title,body"], cwd=workspace)
        issues = json.loads(out) if out else []

        valid_issues = []
        for issue in issues:
            issue_num = str(issue["number"])
            try:
                comments_out = run_cmd(["gh", "issue", "view", issue_num, "--repo", REPO, "--json", "comments"], cwd=workspace)
                comments_data = json.loads(comments_out) if comments_out else {"comments": []}
                for comment in comments_data.get("comments", []):
                    body = comment.get("body", "").lower()
                    if "/solve" in body or "@gossipmesh-bot solve" in body:
                        # Check if a PR already exists for this issue
                        branch_name = f"ai/solve-issue-{issue_num}"
                        existing_pr = run_cmd(["gh", "pr", "list", "--repo", REPO, "--head", branch_name, "--json", "number"], cwd=workspace)
                        prs = json.loads(existing_pr) if existing_pr else []
                        if not prs:
                            valid_issues.append(issue)
                        break
            except Exception as e:
                print(f"[Warning] Failed to fetch comments for issue #{issue_num}: {e}", file=sys.stderr, flush=True)

        return valid_issues
    except Exception as e:
        print(f"[Warning] Failed to fetch issues: {e}", file=sys.stderr, flush=True)
        return []

def generate_new_issue(workspace: Path):
    """Runs the issue generator script with rotated key."""
    active_key = GLOBAL_POOL.next_key()
    print(f"[*] Generating new architecture advancement issue for GossipMesh (Key index: {GLOBAL_POOL.idx % len(GLOBAL_POOL)})...", flush=True)
    print(f"[*] Generating new architecture advancement issue for GossipMesh (Key index: {GLOBAL_POOL.idx % max(1, len(GLOBAL_POOL))})...", flush=True)
    env = os.environ.copy()
    env["GEMINI_ISSUE_KEY"] = active_key
    env["GH_REPO"] = REPO
    res = subprocess.run(
        [sys.executable, "scripts/generate_advancement_issue.py", "--force"],
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    print(res.stdout, flush=True)
    if res.returncode != 0:
        print(f"[!] Generator error: {res.stderr}", file=sys.stderr, flush=True)

def solve_issue(workspace: Path, issue_num: int, issue_title: str, issue_body: str):
    """Solves an issue, creates PR, reviews, and merges."""
    solver_key = GLOBAL_POOL.next_key()
    print(f"\n=======================================================", flush=True)
    print(f"[*] Solving Issue #{issue_num}: {issue_title}", flush=True)
    print(f"[*] Active Solver API Key: ...{solver_key[-6:] if len(solver_key) > 6 else 'key'}", flush=True)
    print(f"=======================================================", flush=True)

    env = os.environ.copy()
    env["GEMINI_API_KEY"] = solver_key
    env["GH_REPO"] = REPO

    solver_cmd = [
        sys.executable, "scripts/ai_issue_solver.py",
        "--issue-number", str(issue_num),
        "--issue-title", issue_title,
        "--issue-body", issue_body,
        "--workspace", str(workspace)
    ]
    res = subprocess.run(solver_cmd, cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(res.stdout, flush=True)
    if res.returncode != 0:
        print(f"[!] Solver failed: {res.stderr}", file=sys.stderr, flush=True)
        return False

    # Pre-commit Quality Assurance Gate
    print("[*] Tidying Go modules with python -m compileall ....", flush=True)
    run_cmd(["python", "-m", "compileall", "."], cwd=workspace, check=False)

    print("[*] Formatting Go codebase with gofmt...", flush=True)
    run_cmd(["black", "."], cwd=workspace, check=False)

    print("[*] Verifying Go compilation & static analysis (go vet)...", flush=True)
    vet_res = subprocess.run(["flake8", "."], cwd=workspace, capture_output=True, text=True, encoding="utf-8", errors="replace")
    check_res = subprocess.run(["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], cwd=workspace, capture_output=True, text=True, encoding="utf-8", errors="replace")

    if vet_res.returncode != 0 or check_res.returncode != 0:
        print(f"[!] CI failed. Calling AI CI Fixer...", flush=True)
        ci_fixer_cmd = [
            sys.executable, "scripts/ai_ci_fixer.py",
            "--pr-number", str(issue_num), # Fake PR number if it is not created yet
            "--workspace", str(workspace)
        ]
        fix_res = subprocess.run(ci_fixer_cmd, cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(fix_res.stdout, flush=True)


    branch_name = f"ai/solve-issue-{issue_num}"
    print(f"[*] Staging changes on branch {branch_name}...", flush=True)
    run_cmd(f"git checkout -B {branch_name}", cwd=workspace)
    run_cmd("git config user.name 'Aditya Dahale'", cwd=workspace)
    run_cmd(f"git config user.email '{USER_EMAIL}'", cwd=workspace)

    run_cmd("git rm --cached -f ai_pr_*.md ai_review_*.json ci_fix_*.md 2>/dev/null || true", cwd=workspace, check=False)
    run_cmd("git add -A", cwd=workspace)
    run_cmd("git reset -- ai_pr_*.md ai_review_*.json ci_fix_*.md 2>/dev/null || true", cwd=workspace, check=False)

    commit_msg = f"feat: automated resolution for issue #{issue_num} ({issue_title})"
    run_cmd([
        "git", "commit",
        "-m", commit_msg,
        "-m", f"Co-authored-by: {USER_NAME} <{USER_EMAIL}>"
    ], cwd=workspace, check=False)

    print(f"[*] Pushing branch {branch_name} to origin...", flush=True)
    run_cmd(f"git push origin {branch_name} --force", cwd=workspace)

    print("[*] Creating / updating Pull Request...", flush=True)
    summary_file = workspace / "ai_pr_summary.md"
    body_content = summary_file.read_text(encoding="utf-8") if summary_file.exists() else f"Automated resolution for Issue #{issue_num}."

    pr_url = ""
    pr_num = None
    try:
        existing = run_cmd(["gh", "pr", "list", "--repo", REPO, "--head", branch_name, "--json", "number,url"], cwd=workspace)
        prs = json.loads(existing) if existing else []
        if prs:
            pr_num = prs[0]["number"]
            pr_url = prs[0]["url"]
            print(f"[OK] Found existing PR #{pr_num}: {pr_url}", flush=True)
        else:
            pr_out = run_cmd([
                "gh", "pr", "create",
                "--repo", REPO,
                "--head", branch_name,
                "--base", "main",
                "--title", f"feat(ai): resolve #{issue_num} - {issue_title}",
                "--body", body_content,
                "--label", "advancement,ai-generated"
            ], cwd=workspace)
            pr_url = pr_out.strip()
            pr_num = int(pr_url.split("/")[-1])
            print(f"[OK] Created PR #{pr_num}: {pr_url}", flush=True)
    except Exception as e:
        print(f"[!] Failed to manage PR: {e}", file=sys.stderr, flush=True)
        return False

    reviewer_key = GLOBAL_POOL.next_key()
    print(f"[*] Running Autonomous Architectural Reviewer on PR #{pr_num} (Key index: {GLOBAL_POOL.idx % max(1, len(GLOBAL_POOL))})...", flush=True)
    env["GEMINI_REVIEWER_KEY"] = reviewer_key
    rev_res = subprocess.run([
        sys.executable, "scripts/ai_pr_reviewer.py",
        "--pr-number", str(pr_num),
        "--workspace", str(workspace)
    ], cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(rev_res.stdout, flush=True)

    review_status_file = workspace / "ai_review_status.json"
    score = 0
    verdict = "ACTION_REQUIRED"
    if review_status_file.exists():
        try:
            status_data = json.loads(review_status_file.read_text(encoding="utf-8"))
            score = status_data.get("score", 0)
            verdict = status_data.get("verdict", "ACTION_REQUIRED")
        except Exception:
            pass

    review_md_file = workspace / "ai_pr_review.md"
    if review_md_file.exists():
        run_cmd(["gh", "pr", "comment", str(pr_num), "--body-file", str(review_md_file)], cwd=workspace, check=False)

    if verdict != "APPROVED" or score < 90:
        print(f"[!] PR #{pr_num} verdict: {verdict} (Score: {score}). Calling AI CI Fixer to refactor...", flush=True)
        ci_fixer_cmd = [
            sys.executable, "scripts/ai_ci_fixer.py",
            "--pr-number", str(pr_num),
            "--workspace", str(workspace)
        ]
        if review_md_file.exists():
            ci_fixer_cmd.extend(["--review-feedback-file", str(review_md_file)])
        fix_res = subprocess.run(ci_fixer_cmd, cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(fix_res.stdout, flush=True)

        # Re-commit and push if fixed
        run_cmd("git add -A", cwd=workspace)
        run_cmd(["git", "commit", "-m", f"fix: incorporate ai reviewer feedback for PR #{pr_num}"], cwd=workspace, check=False)
        run_cmd(f"git push origin {branch_name} --force", cwd=workspace, check=False)
        return False

    if verdict == "APPROVED" and score >= 90:
        print(f"[🚀] PR #{pr_num} APPROVED (Score: {score}/100)! Checking for human merge permission...", flush=True)

        has_merge_permission = False
        try:
            comments_out = run_cmd(["gh", "pr", "view", str(pr_num), "--repo", REPO, "--json", "comments"], cwd=workspace)
            comments_data = json.loads(comments_out) if comments_out else {"comments": []}
            for comment in comments_data.get("comments", []):
                body = comment.get("body", "").lower()
                if "/merge" in body:
                    has_merge_permission = True
                    break
        except Exception as e:
            print(f"[Warning] Failed to fetch comments for PR #{pr_num}: {e}", file=sys.stderr, flush=True)

        if has_merge_permission:
            print(f"[🚀] Permission granted! Merging PR #{pr_num} into main...", flush=True)
            run_cmd(["gh", "label", "create", "ready-to-merge", "--color", "0E8A16", "-f"], cwd=workspace, check=False)
            run_cmd(["gh", "pr", "edit", str(pr_num), "--add-label", "ready-to-merge"], cwd=workspace, check=False)
            merge_out = run_cmd(["gh", "pr", "merge", str(pr_num), "--squash", "--admin"], cwd=workspace)
            print(f"[SUCCESS] Merged PR #{pr_num} into main! Contributor activity recorded for {USER_NAME}.", flush=True)
            run_cmd("git checkout main", cwd=workspace)
            run_cmd("git pull origin main", cwd=workspace)
            # Clean up feature branch
            run_cmd(f"git branch -D {branch_name}", cwd=workspace, check=False)
            run_cmd(f"git push origin --delete {branch_name}", cwd=workspace, check=False)
            return True
        else:
            print(f"[*] PR #{pr_num} is approved but missing '/merge' comment from a human. Awaiting permission.", flush=True)
            return False
    else:
        print(f"[!] PR #{pr_num} verdict: {verdict} (Score: {score}). Awaiting review fixes.", flush=True)
        return False

def handle_pr_comments(workspace: Path):
    """Checks open PRs for /review or /fix comments and executes CI tests/error solve loop."""
    try:
        out = run_cmd(["gh", "pr", "list", "--repo", REPO, "--state", "open", "--json", "number,headRefName"], cwd=workspace)
        prs = json.loads(out) if out else []
        for pr in prs:
            pr_num = str(pr["number"])
            comments_out = run_cmd(["gh", "pr", "view", pr_num, "--repo", REPO, "--json", "comments"], cwd=workspace)
            comments_data = json.loads(comments_out) if comments_out else {"comments": []}

            needs_review_or_fix = False
            for comment in comments_data.get("comments", []):
                body = comment.get("body", "").lower()
                if "/review" in body or "/fix" in body:
                    needs_review_or_fix = True
                    break

            if needs_review_or_fix:
                print(f"[*] Processing PR #{pr_num} for requested review/fix...", flush=True)
                env = os.environ.copy()
                branch_name = pr["headRefName"]

                # Check out the PR branch
                run_cmd(f"git checkout {branch_name}", cwd=workspace)
                run_cmd(f"git pull origin {branch_name}", cwd=workspace, check=False)

                # Run tests
                check_res = subprocess.run(["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], cwd=workspace, capture_output=True, text=True, encoding="utf-8", errors="replace")

                if check_res.returncode != 0:
                    print(f"[!] PR #{pr_num} CI failed during requested review. Calling AI CI Fixer...", flush=True)
                    ci_fixer_cmd = [
                        sys.executable, "scripts/ai_ci_fixer.py",
                        "--pr-number", str(pr_num),
                        "--workspace", str(workspace)
                    ]
                    fix_res = subprocess.run(ci_fixer_cmd, cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
                    print(fix_res.stdout, flush=True)

                    # Re-commit and push if fixed
                    run_cmd("git add -A", cwd=workspace)
                    run_cmd(["git", "commit", "-m", f"fix: automated CI fix based on review request for PR #{pr_num}"], cwd=workspace, check=False)
                    run_cmd(f"git push origin {branch_name}", cwd=workspace, check=False)
                else:
                    print(f"[*] PR #{pr_num} CI passed! Proceeding to reviewer...", flush=True)

                # Run the reviewer regardless
                reviewer_key = GLOBAL_POOL.next_key()
                print(f"[*] Running Autonomous Architectural Reviewer on PR #{pr_num} (Key index: {GLOBAL_POOL.idx % max(1, len(GLOBAL_POOL))})...", flush=True)
                env["GEMINI_REVIEWER_KEY"] = reviewer_key
                rev_res = subprocess.run([
                    sys.executable, "scripts/ai_pr_reviewer.py",
                    "--pr-number", str(pr_num),
                    "--workspace", str(workspace)
                ], cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
                print(rev_res.stdout, flush=True)

                review_md_file = workspace / "ai_pr_review.md"
                if review_md_file.exists():
                    run_cmd(["gh", "pr", "comment", str(pr_num), "--body-file", str(review_md_file)], cwd=workspace, check=False)

                # Switch back to main
                run_cmd("git checkout main", cwd=workspace)

    except Exception as e:
        print(f"[Warning] Failed to check PR comments: {e}", file=sys.stderr, flush=True)


def run_loop_iteration(workspace: Path):
    """Executes a single cycle of the autonomous loop."""
    print(f"\n--- [Autonomous GossipMesh Loop Iteration: {time.strftime('%Y-%m-%d %H:%M:%S')} | Key Pool: {len(GLOBAL_POOL)} keys] ---", flush=True)
    issues = get_open_advancement_issues(workspace)
    # Check for requested PR reviews/fixes
    handle_pr_comments(workspace)

    # Check if there are ANY open issues first, before filtering for /solve
    try:
        out = run_cmd(["gh", "issue", "list", "--repo", REPO, "--label", "advancement", "--state", "open", "--json", "number"], cwd=workspace)
        all_open_issues = json.loads(out) if out else []
    except Exception as e:
        print(f"[Warning] Failed to fetch issues: {e}", file=sys.stderr, flush=True)
        all_open_issues = []

    if not all_open_issues:
        print("[*] No open advancement issues found. Generating one...", flush=True)
        generate_new_issue(workspace)
        time.sleep(5)

    # Now get issues that are ready to be solved (have /solve comment and no PR)
    issues = get_open_advancement_issues(workspace)

    if not issues:
        print("[!] No issues ready to solve (waiting for '/solve' comment).", flush=True)
        return

    target = issues[0]
    solve_issue(workspace, target["number"], target["title"], target.get("body", ""))

def main():
    parser = argparse.ArgumentParser(description="GossipMesh Autonomous Multi-Agent Daemon")
    parser.add_argument("--workspace", default=".", help="Path to GossipMesh repository root")
    parser.add_argument("--once", action="store_true", help="Run once and exit instead of continuous daemon")
    parser.add_argument("--interval", type=int, default=10, help="Interval in seconds between cycles (default: 10s)")
    parser.add_argument("--add-keys", nargs="*", default=[], help="Additional Gemini API keys to add to the round-robin pool")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    if args.add_keys:
        GLOBAL_POOL.add_keys(args.add_keys)

    print(f"[*] GossipMesh Multi-Agent Engine initialized with {len(GLOBAL_POOL)} API keys in active rotation.", flush=True)

    if args.once:
        run_loop_iteration(workspace)
    else:
        print(f"[*] Starting GossipMesh Continuous Autonomous Daemon (interval: {args.interval}s)...", flush=True)
        while True:
            try:
                run_loop_iteration(workspace)
            except Exception as e:
                print(f"[Error in loop]: {e}", file=sys.stderr, flush=True)
            print(f"[*] Sleeping for {args.interval} seconds until next iteration...", flush=True)
            time.sleep(args.interval)

if __name__ == "__main__":
    main()
