#!/usr/bin/env python3
"""GossipMesh Balanced Dual-Pool 24/7 Engine

Distributes available compute and AI keys 50/50:
- PR Pool (4 Workers): Autonomous architectural reviews, security audits, and quality gating.
- Issue Pool (4 Workers): Issue necessity gating, solution synthesis, test generation, and automated PR creation.

Supports any target repository (--repo / GH_REPO).
"""

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEWER_SCRIPT = REPO_ROOT / "scripts" / "ai_pr_reviewer.py"
ISSUE_APPROVER_SCRIPT = REPO_ROOT / "scripts" / "ai_issue_approver.py"
ISSUE_SOLVER_SCRIPT = REPO_ROOT / "scripts" / "ai_issue_solver.py"


def run_cmd(cmd, cwd=None, env=None):
    return subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        env=env or os.environ.copy(),
    )


def get_open_prs(repo: str = None) -> list[str]:
    cmd = ["gh", "pr", "list", "--state", "open", "--json", "number", "--jq", ".[].number"]
    if repo:
        cmd.extend(["--repo", repo])
    res = run_cmd(cmd)
    if res.returncode == 0:
        return [l.strip() for l in res.stdout.splitlines() if l.strip()]
    return []


def get_open_issues(repo: str = None) -> list[dict]:
    cmd = [
        "gh",
        "issue",
        "list",
        "--state",
        "open",
        "--json",
        "number,title,body,labels",
        "--limit",
        "25",
    ]
    if repo:
        cmd.extend(["--repo", repo])
    res = run_cmd(cmd)
    if res.returncode == 0 and res.stdout.strip():
        try:
            return json.loads(res.stdout)
        except Exception:
            return []
    return []


def review_single_pr(pr_number: str, repo: str = None, workspace: str = None):
    cmd = [sys.executable, str(REVIEWER_SCRIPT), "--pr-number", str(pr_number)]
    if workspace:
        cmd.extend(["--workspace", str(workspace)])
    env = os.environ.copy()
    if repo:
        env["GH_REPO"] = repo
        env["GITHUB_REPOSITORY"] = repo
    try:
        res = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
        status = "OK" if res.returncode == 0 else f"FAIL (exit {res.returncode})"
        return ("PR", pr_number, status, res.stderr[-200:] if res.stderr else "")
    except Exception as e:
        return ("PR", pr_number, f"EXCEPTION: {e}", str(e))


def process_single_issue(issue: dict, repo: str = None, workspace: str = None):
    issue_num = str(issue.get("number"))
    title = issue.get("title", "")
    body = issue.get("body", "") or ""
    labels = [l.get("name", "") for l in issue.get("labels", [])]

    env = os.environ.copy()
    if repo:
        env["GH_REPO"] = repo
        env["GITHUB_REPOSITORY"] = repo

    # 1. Gatekeeper evaluation if not yet reviewed
    is_approved = any(l in ("approved", "auto-solve", "advancement") for l in labels)

    if not is_approved and ISSUE_APPROVER_SCRIPT.is_file():
        print(f"[*] [Issue Worker] Evaluating necessity of Issue #{issue_num}: {title[:50]}...")
        eval_cmd = [
            sys.executable,
            str(ISSUE_APPROVER_SCRIPT),
            "--issue-number",
            issue_num,
            "--issue-title",
            title,
            "--issue-body",
            body,
            "--workspace",
            str(workspace or "."),
        ]
        res = subprocess.run(eval_cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env, timeout=120)
        if res.returncode == 0:
            is_approved = True

    # 2. If approved or labeled for advancement, trigger solution synthesis
    if is_approved and ISSUE_SOLVER_SCRIPT.is_file():
        print(f"[*] [Issue Worker] Synthesizing automated solution for Issue #{issue_num}...")
        solve_cmd = [
            sys.executable,
            str(ISSUE_SOLVER_SCRIPT),
            "--issue-number",
            issue_num,
            "--issue-title",
            title,
            "--issue-body",
            body,
            "--workspace",
            str(workspace or "."),
        ]
        try:
            res = subprocess.run(solve_cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env, timeout=300)
            status = "SOLVED" if res.returncode == 0 else f"SOLVE_FAIL (exit {res.returncode})"
            return ("ISSUE", issue_num, status, res.stderr[-200:] if res.stderr else "")
        except Exception as e:
            return ("ISSUE", issue_num, f"EXCEPTION: {e}", str(e))

    return ("ISSUE", issue_num, "SKIPPED_OR_TRIAGED", "")


def main():
    parser = argparse.ArgumentParser(description="GossipMesh 50/50 Dual-Pool Autonomous Engine")
    parser.add_argument("--repo", default=os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--pr-workers", type=int, default=4, help="Number of PR review workers")
    parser.add_argument("--issue-workers", type=int, default=4, help="Number of Issue resolution workers")
    args = parser.parse_args()

    repo = args.repo
    print("=" * 60)
    print(f"[*] GossipMesh 50/50 Balanced Dual-Pool Active on: {repo or 'Current Repository'}")
    print(f"[*] Allocation: {args.pr_workers} PR Review Workers | {args.issue_workers} Issue Solver Workers")
    print("=" * 60)

    pr_numbers = get_open_prs(repo)
    open_issues = get_open_issues(repo)

    print(f"[*] Discovered: {len(pr_numbers)} open PR(s), {len(open_issues)} open Issue(s).")

    total_tasks = []

    # Run PR reviews in Pool A
    with ThreadPoolExecutor(max_workers=max(1, args.pr_workers)) as pr_executor:
        pr_futures = [
            pr_executor.submit(review_single_pr, pr, repo, args.workspace)
            for pr in pr_numbers[:10]  # Process up to 10 PRs per cycle
        ]

        # Run Issue evaluations/solving in Pool B simultaneously
        with ThreadPoolExecutor(max_workers=max(1, args.issue_workers)) as issue_executor:
            issue_futures = [
                issue_executor.submit(process_single_issue, issue, repo, args.workspace)
                for issue in open_issues[:10]  # Process up to 10 issues per cycle
            ]

            all_futures = pr_futures + issue_futures
            for future in as_completed(all_futures):
                try:
                    task_type, item_id, status, details = future.result()
                    print(f"[{task_type}] #{item_id}: {status}")
                    if details:
                        print(f"    Detail: {details.strip()}")
                except Exception as exc:
                    print(f"[!] Worker exception: {exc}")

    print("=" * 60)
    print("[✓] Dual-Pool 50/50 cycle finished successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
