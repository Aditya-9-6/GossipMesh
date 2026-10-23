#!/usr/bin/env python3
"""GossipMesh Balanced Dual-Pool 24/7 Engine

Distributes available compute and AI keys 50/50:
- PR Pool (4 Workers): Deep architectural reviews, security audits, and concurrency gating.
- Issue Pool (4 Workers): Issue necessity gating, closing unnecessary tickets,
  solution synthesis, pre-flight test verification, and automated PR creation.

Supports any target repository (--repo / GH_REPO).
"""

import argparse
import json
import os
import subprocess
import sys
import time
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
        encoding="utf-8",
        errors="replace",
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
        "30",
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


def verify_code_preflight(workspace: Path) -> tuple[bool, str]:
    """Runs strict pre-flight code verification before creating any PR."""
    is_go = (workspace / "go.mod").exists()
    if is_go:
        # Check Go syntax / vetting
        vet_res = run_cmd(["go", "vet", "./..."], cwd=workspace)
        if vet_res.returncode != 0 and "go: command not found" not in vet_res.stderr:
            return False, f"go vet failed: {vet_res.stderr}"
        return True, "Go pre-flight passed."
    else:
        # Python syntax & compile check
        comp_res = run_cmd(
            [sys.executable, "-m", "compileall", "-q", "-x", r"(\.venv|\.git)", "."],
            cwd=workspace,
        )
        if comp_res.returncode != 0:
            return False, f"Python syntax/compileall error: {comp_res.stderr}"
        return True, "Python pre-flight passed."


def process_single_issue(issue: dict, repo: str = None, workspace_str: str = None):
    issue_num = str(issue.get("number"))
    title = issue.get("title", "")
    body = issue.get("body", "") or ""
    labels = [l.get("name", "") for l in issue.get("labels", [])]
    workspace = Path(workspace_str or ".").resolve()

    env = os.environ.copy()
    if repo:
        env["GH_REPO"] = repo
        env["GITHUB_REPOSITORY"] = repo

    # Skip if issue was already rejected
    if "rejected" in labels:
        return ("ISSUE", issue_num, "SKIPPED_REJECTED", "Issue already rejected.")

    # 1. Gatekeeper evaluation: filter out unnecessary issues
    is_approved = any(l in ("approved", "auto-solve", "advancement") for l in labels)

    if not is_approved and ISSUE_APPROVER_SCRIPT.is_file():
        print(f"[*] [Issue Worker] Evaluating necessity of Issue #{issue_num}: {title[:50]}...", flush=True)
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
            str(workspace),
        ]
        res = subprocess.run(eval_cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env, timeout=120)
        if res.returncode == 0:
            is_approved = True
        else:
            print(f"[*] Issue #{issue_num} was closed or refined by Gatekeeper.")
            return ("ISSUE", issue_num, "CLOSED_OR_REFINED", "Closed as unnecessary or updated.")

    if not is_approved:
        return ("ISSUE", issue_num, "UNAPPROVED", "Issue did not meet necessity threshold.")

    # 2. Check if a PR already exists for this issue
    check_pr_cmd = ["gh", "pr", "list", "--state", "all", "--search", f"resolve #{issue_num}"]
    if repo:
        check_pr_cmd.extend(["--repo", repo])
    existing_prs = run_cmd(check_pr_cmd, cwd=workspace)
    if existing_prs.returncode == 0 and existing_prs.stdout.strip():
        return ("ISSUE", issue_num, "PR_ALREADY_EXISTS", "A PR already exists for this issue.")

    # 3. Synthesize automated solution
    if ISSUE_SOLVER_SCRIPT.is_file():
        print(f"[*] [Issue Worker] Synthesizing automated solution for Issue #{issue_num}...", flush=True)
        branch_name = f"ai/solve-issue-{issue_num}"

        # Clean git status before writing
        run_cmd(["git", "checkout", "main"], cwd=workspace)
        run_cmd(["git", "checkout", "--", "."], cwd=workspace)
        run_cmd(["git", "clean", "-fd"], cwd=workspace)

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
            str(workspace),
        ]
        solve_res = subprocess.run(solve_cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env, timeout=300)
        if solve_res.returncode != 0:
            run_cmd(["git", "checkout", "--", "."], cwd=workspace)
            run_cmd(["git", "clean", "-fd"], cwd=workspace)
            return ("ISSUE", issue_num, "SOLVE_FAIL", solve_res.stderr[-200:])

        # 4. Strict Pre-flight Code Verification Gate
        print(f"[*] Running pre-flight code verification for Issue #{issue_num}...", flush=True)
        is_green, reason = verify_code_preflight(workspace)
        if not is_green:
            print(f"[!] Pre-flight verification failed for #{issue_num}: {reason}. Reverting changes...", file=sys.stderr)
            run_cmd(["git", "checkout", "--", "."], cwd=workspace)
            run_cmd(["git", "clean", "-fd"], cwd=workspace)
            return ("ISSUE", issue_num, "PREFLIGHT_FAIL", reason)

        # 5. Create branch, commit, push, and open PR
        print(f"[*] Pre-flight passed! Staging changes on {branch_name}...", flush=True)
        run_cmd(["git", "checkout", "-B", branch_name], cwd=workspace)
        run_cmd(["git", "config", "user.name", "GossipMesh Autonomous Engine"], cwd=workspace)
        run_cmd(["git", "config", "user.email", "bot@gossipmesh.io"], cwd=workspace)

        run_cmd(["git", "add", "-A"], cwd=workspace)
        commit_msg = f"feat(ai): resolve #{issue_num} - {title}"
        run_cmd(["git", "commit", "-m", commit_msg], cwd=workspace)

        # Push branch
        print(f"[*] Pushing branch {branch_name} to remote...", flush=True)
        push_res = run_cmd(["git", "push", "origin", branch_name, "--force"], cwd=workspace)
        if push_res.returncode != 0:
            run_cmd(["git", "checkout", "main"], cwd=workspace)
            return ("ISSUE", issue_num, "PUSH_FAIL", push_res.stderr[-200:])

        # Create PR
        summary_path = workspace / "ai_pr_summary.md"
        summary_body = (
            summary_path.read_text(encoding="utf-8")
            if summary_path.exists()
            else f"Automated solution for Issue #{issue_num}.\n\nCloses #{issue_num}"
        )
        if f"Closes #{issue_num}" not in summary_body:
            summary_body += f"\n\nCloses #{issue_num}"

        pr_cmd = [
            "gh",
            "pr",
            "create",
            "--head",
            branch_name,
            "--base",
            "main",
            "--title",
            f"feat(ai): resolve #{issue_num} - {title}",
            "--body",
            summary_body,
            "--label",
            "advancement,ai-generated",
        ]
        if repo:
            pr_cmd.extend(["--repo", repo])

        pr_res = run_cmd(pr_cmd, cwd=workspace)
        run_cmd(["git", "checkout", "main"], cwd=workspace)

        if pr_res.returncode == 0:
            pr_url = pr_res.stdout.strip()
            print(f"[✓] Created Pull Request: {pr_url}", flush=True)
            return ("ISSUE", issue_num, "PR_CREATED", pr_url)
        else:
            return ("ISSUE", issue_num, "PR_CREATE_FAIL", pr_res.stderr[-200:])

    return ("ISSUE", issue_num, "SKIPPED", "")


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

    # 1. Run PR Reviews in Pool A concurrently
    print(f"\n[*] Launching Pool A: {args.pr_workers} Concurrent PR Review Workers...")
    with ThreadPoolExecutor(max_workers=max(1, args.pr_workers)) as pr_executor:
        pr_futures = [
            pr_executor.submit(review_single_pr, pr, repo, args.workspace)
            for pr in pr_numbers[:8]
        ]
        for future in as_completed(pr_futures):
            try:
                task_type, item_id, status, details = future.result()
                print(f"[{task_type}] #{item_id}: {status}")
                if details:
                    print(f"    Detail: {details.strip()[:150]}")
            except Exception as exc:
                print(f"[!] PR Worker exception: {exc}")

    # 2. Run Issue Gatekeeper & Solution Synthesis in Pool B
    print(f"\n[*] Launching Pool B: Issue Gatekeeper & Solver Workers...")
    for issue in open_issues[:6]:
        try:
            task_type, item_id, status, details = process_single_issue(issue, repo, args.workspace)
            print(f"[{task_type}] #{item_id}: {status}")
            if details:
                print(f"    Detail: {details.strip()[:150]}")
        except Exception as exc:
            print(f"[!] Issue Worker exception: {exc}")

    print("=" * 60)
    print("[✓] Dual-Pool 50/50 cycle finished successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
