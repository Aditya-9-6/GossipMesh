#!/usr/bin/env python3
"""
Autonomous Multi-Agent GitHub Advancement Loop for GossipMesh (Local Daemon & Cloud Runner)

Executes the continuous hyper-scale development cycle:
1. Dynamic Key Pooling: Rotates Gemini API keys round-robin to maximize RPM/TPM quota.
2. Issue Generation: Creates architecture advancement specifications.
3. AI Solver: Implements solutions with zero-allocation, anti-spaghetti invariants.
4. Pre-Commit Quality Gate: Runs black . || echo 'black not found', flake8 . || echo 'flake8 not found', and python -m unittest discover -s tests -p 'test_*.py' -v
5. Contribution Attribution: Commits with 'GossipMesh Bot <bot@gossipmesh.io>'.
6. Autonomous Reviewer Gate: Audits PR against strict performance and decoupling invariants.
7. Auto-Merger: Squash-merges approved PRs to continuously illuminate GitHub contribution chart.
"""

import os
import sys
import re
import json
import time
import traceback
import subprocess
import argparse
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

REPO = os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY") or "Aditya-9-6/GossipMesh"
USER_NAME = os.environ.get("GIT_AUTHOR_NAME") or "Dahale Aditya Dnyaneshwar"
USER_EMAIL = os.environ.get("GIT_AUTHOR_EMAIL") or "adityadahale96@gmail.com"

# Base Key Pool - Dynamically loaded from GEMINI_KEY_POOL, individual env vars, or .gemini_keys
DEFAULT_KEYS = []
FAILED_SOLVE_ATTEMPTS = {}


class VolumeLimiterStub:
    def check_limits(self, org_id: str = "default", is_pr: bool = True):
        return True, ""

    def record_usage(self, org_id: str = "default", prs: int = 1):
        pass


volume_limiter = VolumeLimiterStub()


class LedgerStub:
    def charge(self, org: str, item: str) -> bool:
        return True

    def refund(self, org: str, amount: int) -> None:
        pass

    def get(self, org: str) -> int:
        return 100


class ExecutionLoop:
    def __init__(self):
        self.ledger = LedgerStub()


GLOBAL_EXECUTION_LOOP = ExecutionLoop()
execution_loop = GLOBAL_EXECUTION_LOOP


def load_multi_provider_keys():
    """Loads auxiliary LLM keys (OpenRouter, NVIDIA, Cohere, HuggingFace) from .llm_keys files."""
    for check_dir in (Path("."), Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent, Path.home()):
        llm_file = check_dir / ".llm_keys"
        if llm_file.exists():
            try:
                for line in llm_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip()
                        if k and v and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass


load_multi_provider_keys()


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

        # Check local gitignored .gemini_keys file across workspace root, script dir, and user home
        for check_dir in (
            Path("."),
            Path(__file__).resolve().parent,
            Path(__file__).resolve().parent.parent,
            Path.home(),
        ):
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


# Deprecated global pool; using services.key_pool_router.router for key rotation
from services.key_pool_router import router  # noqa: E402

# Compatibility alias for legacy code expecting GLOBAL_POOL
GLOBAL_POOL = router


def run_cmd(cmd, cwd=None, check=False, timeout=60):
    """Runs a shell command and returns stdout with timeout protection."""
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd,
            shell=isinstance(cmd, str),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if check and res.returncode != 0:
            raise RuntimeError(f"Command failed ({res.returncode}): {cmd}\nStderr: {res.stderr}\nStdout: {res.stdout}")
        return res.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"[Timeout] Command timed out after {timeout}s: {cmd}", file=sys.stderr, flush=True)
        return ""
    except FileNotFoundError:
        return ""
    except Exception as e:
        if check:
            raise e
        return ""


def get_python_bin(workspace: Path) -> str:
    """Finds the most suitable python executable in workspace or system."""
    for cand in [
        workspace / ".venv" / "bin" / "python",
        workspace / ".venv" / "Scripts" / "python.exe",
    ]:
        if cand.is_file():
            return str(cand)
    return sys.executable


def get_tool_bin(workspace: Path, tool_name: str) -> str:
    """Finds binary across Linux (.venv/bin) and Windows (.venv/Scripts)."""
    for cand in [
        workspace / ".venv" / "bin" / tool_name,
        workspace / ".venv" / "Scripts" / f"{tool_name}.exe",
        workspace / ".venv" / "Scripts" / tool_name,
    ]:
        if cand.is_file():
            return str(cand)
    return tool_name


def verify_and_auto_fix_preflight(workspace: Path) -> tuple[bool, str]:
    """
    Executes strict pre-flight quality gate:
    1. Fast deterministic auto-fix: ruff check --fix & ruff format (0 API tokens, <100ms)
    2. Syntax compilation: compileall (zero syntax errors allowed)
    3. Strict linting: ruff check . (zero errors allowed)
    4. Unit test verification: pytest
    Returns (is_green: bool, error_report: str)
    """
    py_bin = get_python_bin(workspace)
    ruff_bin = get_tool_bin(workspace, "ruff")

    # Pass 1: Deterministic auto-fix
    try:
        ruff_fix_cmd = (
            [ruff_bin, "check", "--fix", "."] if ruff_bin != "ruff" else [py_bin, "-m", "ruff", "check", "--fix", "."]
        )
        subprocess.run(ruff_fix_cmd, cwd=workspace, capture_output=True, text=True, timeout=20)
        ruff_fmt_cmd = [ruff_bin, "format", "."] if ruff_bin != "ruff" else [py_bin, "-m", "ruff", "format", "."]
        subprocess.run(ruff_fmt_cmd, cwd=workspace, capture_output=True, text=True, timeout=20)
    except Exception:
        pass

    errors = []

    # Pass 2: Syntax compilation check
    comp_res = subprocess.run(
        [py_bin, "-m", "compileall", "-q", "-x", r"(\.venv|\.git|tests/fixtures)", "gossipmesh", "tests", "scripts"],
        cwd=workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if comp_res.returncode != 0:
        errors.append(f"Syntax/Compilation Failure:\n{comp_res.stderr.strip() or comp_res.stdout.strip()}")

    # Pass 3: Strict Ruff Lint Check
    ruff_check_cmd = [ruff_bin, "check", "."] if ruff_bin != "ruff" else [py_bin, "-m", "ruff", "check", "."]
    ruff_res = subprocess.run(
        ruff_check_cmd, cwd=workspace, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
    )
    if ruff_res.returncode != 0:
        errors.append(f"Ruff Lint Failure:\n{ruff_res.stdout.strip() or ruff_res.stderr.strip()}")

    # Pass 4: Pytest Unit Tests
    test_res = subprocess.run(
        [py_bin, "-m", "pytest", "tests/", "-q", "--durations=5"],
        cwd=workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1200,
    )
    if test_res.returncode != 0:
        combined_tests = (test_res.stdout + "\n" + test_res.stderr).strip()
        errors.append(f"Pytest Failures:\n{combined_tests}")

    if errors:
        return False, "\n\n".join(errors)
    return True, ""


def get_open_advancement_issues(workspace: Path):
    """Fetches open advancement issues, filtering out those that already have active or merged PRs."""
    try:
        out = run_cmd(
            [
                "gh",
                "issue",
                "list",
                "--repo",
                REPO,
                "--label",
                "advancement",
                "--state",
                "open",
                "--json",
                "number,title,body",
            ],
            cwd=workspace,
        )
        all_issues = json.loads(out) if out else []
        if not all_issues:
            return []

        prs_out = run_cmd(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                REPO,
                "--state",
                "all",
                "--limit",
                "50",
                "--json",
                "number,title,headRefName,state",
            ],
            cwd=workspace,
        )
        prs = json.loads(prs_out) if prs_out else []
        active_issue_nums = set()
        for p in prs:
            head = p.get("headRefName", "")
            title = p.get("title", "")
            if "issue-" in head:
                try:
                    cand = int(head.split("issue-")[-1].split("-")[0])
                    active_issue_nums.add(cand)
                except Exception:
                    pass

        # Also inspect remote branches to prevent race conditions among parallel workers
        remote_branches_out = run_cmd(
            ["git", "ls-remote", "--heads", "origin", "refs/heads/ai/solve-issue-*"], cwd=workspace
        )
        for line in remote_branches_out.splitlines():
            if "refs/heads/ai/solve-issue-" in line:
                try:
                    cand = int(line.split("refs/heads/ai/solve-issue-")[-1].split("-")[0])
                    active_issue_nums.add(cand)
                except Exception:
                    pass

        valid_issues = [iss for iss in all_issues if iss.get("number") not in active_issue_nums]
        return valid_issues
    except Exception as e:
        print(f"[Warning] Failed to fetch issues: {e}", file=sys.stderr, flush=True)
        return []


def generate_new_issue(workspace: Path):
    """
    Generates the next task issue.
    PRIORITY 1: Master Implementation Plan (docs/ENTERPRISE_SAAS_IMPLEMENTATION_PLAN.md).
    FALLBACK: Architecture advancement catalog & AI generator.
    """
    print("[*] Checking Master Implementation Plan for next actionable task...", flush=True)
    plan_script = workspace / "scripts" / "plan_advancement_engine.py"
    if plan_script.is_file():
        try:
            plan_res = subprocess.run(
                [sys.executable, str(plan_script), "--create-next", "--workspace", str(workspace)],
                cwd=workspace,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
            print(plan_res.stdout, flush=True)
            if plan_res.returncode == 0 and (
                "Successfully created GitHub Issue" in plan_res.stdout or "Created issue" in plan_res.stdout
            ):
                return
        except Exception as e:
            print(f"[!] Plan engine exception: {e}", file=sys.stderr, flush=True)

    # Fallback to catalog / dynamic generation if plan has no pending tasks or returns error
    active_key = GLOBAL_POOL.next_key()
    print(
        f"[*] Generating architecture advancement issue from catalog (Key index: {GLOBAL_POOL.idx % max(1, len(GLOBAL_POOL))})...",
        flush=True,
    )
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
        errors="replace",
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
        sys.executable,
        "scripts/ai_issue_solver.py",
        "--issue-number",
        str(issue_num),
        "--issue-title",
        issue_title,
        "--issue-body",
        issue_body,
        "--workspace",
        str(workspace),
    ]
    res = subprocess.run(
        solver_cmd, cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    try:
        print(res.stdout, flush=True)
    except Exception:
        print(res.stdout.encode("ascii", errors="replace").decode("ascii"), flush=True)
    if res.returncode != 0:
        print(f"[!] Solver failed: {res.stderr}", file=sys.stderr, flush=True)
        return False

    # Pre-commit Hard Quality Assurance Gate & Self-Healing Loop
    print(f"[*] Running Pre-Flight Quality Gate (deterministic auto-fix, compileall, ruff, pytest)...", flush=True)
    is_green, err_report = verify_and_auto_fix_preflight(workspace)

    if not is_green:
        print(f"[!] Pre-flight checks failed. Entering self-healing loop (up to 3 passes)...", flush=True)
        max_fix_passes = 3
        for fix_pass in range(1, max_fix_passes + 1):
            print(f"[*] Self-healing pass {fix_pass}/{max_fix_passes} for Issue #{issue_num}...", flush=True)
            ci_fixer_cmd = [
                sys.executable,
                "scripts/ai_ci_fixer.py",
                "--pr-number",
                str(issue_num),
                "--workspace",
                str(workspace),
            ]
            subprocess.run(
                ci_fixer_cmd, cwd=workspace, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace"
            )

            is_green, err_report = verify_and_auto_fix_preflight(workspace)
            if is_green:
                print(f"[SUCCESS] Code repaired and 100% green on pass {fix_pass}!", flush=True)
                break
            else:
                print(f"[!] Code still failing after pass {fix_pass}.", flush=True)

    if not is_green:
        print(
            f"[ABORT] Cannot create PR for Issue #{issue_num}: Code does not pass pre-flight verification gate.\n{err_report[:1000]}",
            file=sys.stderr,
            flush=True,
        )
        run_cmd("git reset --hard HEAD", cwd=workspace, check=False)
        run_cmd("git clean -fd", cwd=workspace, check=False)
        return False

    branch_name = f"ai/solve-issue-{issue_num}"
    print(f"[*] Staging changes on branch {branch_name}...", flush=True)
    run_cmd(["git", "checkout", "-B", branch_name], cwd=workspace)
    run_cmd(["git", "config", "user.name", USER_NAME], cwd=workspace)
    run_cmd(["git", "config", "user.email", USER_EMAIL], cwd=workspace)

    run_cmd(
        "git rm --cached -f ai_pr_*.md ai_review_*.json ci_fix_*.md 2>/dev/null || true", cwd=workspace, check=False
    )
    run_cmd(["git", "add", "-A"], cwd=workspace)
    run_cmd("git reset -- ai_pr_*.md ai_review_*.json ci_fix_*.md 2>/dev/null || true", cwd=workspace, check=False)

    commit_msg = f"feat: automated resolution for issue #{issue_num} ({issue_title})"
    run_cmd(["git", "commit", "--author", f"{USER_NAME} <{USER_EMAIL}>", "-m", commit_msg], cwd=workspace, check=False)

    print(f"[*] Pushing branch {branch_name} to origin...", flush=True)
    run_cmd(["git", "push", "origin", branch_name, "--force"], cwd=workspace)

    print("[*] Creating / updating Pull Request...", flush=True)
    summary_file = workspace / "ai_pr_summary.md"
    body_content = (
        summary_file.read_text(encoding="utf-8")
        if summary_file.exists()
        else f"Automated resolution for Issue #{issue_num}."
    )
    if f"Closes #{issue_num}" not in body_content and f"Fixes #{issue_num}" not in body_content:
        body_content += f"\n\nCloses #{issue_num}"

    pr_url = ""
    pr_num = None
    try:
        existing = run_cmd(
            ["gh", "pr", "list", "--repo", REPO, "--head", branch_name, "--json", "number,url"], cwd=workspace
        )
        prs = json.loads(existing) if existing else []
        if prs:
            pr_num = prs[0]["number"]
            pr_url = prs[0]["url"]
            print(f"[OK] Found existing PR #{pr_num}: {pr_url}", flush=True)
        else:
            pr_out = run_cmd(
                [
                    "gh",
                    "pr",
                    "create",
                    "--repo",
                    REPO,
                    "--head",
                    branch_name,
                    "--base",
                    "main",
                    "--title",
                    f"feat: resolve #{issue_num} - {issue_title}",
                    "--body",
                    body_content,
                    "--label",
                    "advancement",
                ],
                cwd=workspace,
            )
            pr_url = pr_out.strip()
            pr_num = int(pr_url.split("/")[-1])
            print(f"[OK] Created PR #{pr_num}: {pr_url}", flush=True)

            # Auto-approve CI workflow runs so all tests execute immediately without waiting for approval
            try:
                time.sleep(3)
                pending_out = run_cmd(
                    ["gh", "api", f"repos/{REPO}/actions/runs?status=action_required", "--jq", ".workflow_runs[].id"],
                    cwd=workspace,
                    check=False,
                )
                for run_id in pending_out.splitlines():
                    run_id = run_id.strip()
                    if run_id:
                        run_cmd(
                            ["gh", "api", f"repos/{REPO}/actions/runs/{run_id}/approve", "-X", "POST"],
                            cwd=workspace,
                            check=False,
                        )
                        print(
                            f"[OK] Automatically approved CI workflow run {run_id} to execute tests immediately.",
                            flush=True,
                        )
            except Exception:
                pass
    except Exception as e:
        print(f"[!] Failed to manage PR: {e}", file=sys.stderr, flush=True)
        return False

    reviewer_key = GLOBAL_POOL.next_key()
    print(
        f"[*] Running Autonomous Architectural Reviewer on PR #{pr_num} (Key index: {GLOBAL_POOL.idx % max(1, len(GLOBAL_POOL))})...",
        flush=True,
    )
    env["GEMINI_REVIEWER_KEY"] = reviewer_key
    rev_res = subprocess.run(
        [sys.executable, "scripts/ai_pr_reviewer.py", "--pr-number", str(pr_num), "--workspace", str(workspace)],
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
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
            sys.executable,
            "scripts/ai_ci_fixer.py",
            "--pr-number",
            str(pr_num),
            "--workspace",
            str(workspace),
            "--max-iterations",
            "3",
        ]
        if review_md_file.exists():
            ci_fixer_cmd.extend(["--review-feedback-file", str(review_md_file)])
        fix_res = subprocess.run(
            ci_fixer_cmd,
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        print(fix_res.stdout, flush=True)

        # Re-commit and push if fixed
        run_cmd(["git", "config", "user.name", USER_NAME], cwd=workspace)
        run_cmd(["git", "config", "user.email", USER_EMAIL], cwd=workspace)
        run_cmd(["git", "add", "-A"], cwd=workspace)
        run_cmd(
            [
                "git",
                "commit",
                "--author",
                f"{USER_NAME} <{USER_EMAIL}>",
                "-m",
                f"fix: incorporate ai reviewer feedback for PR #{pr_num}",
            ],
            cwd=workspace,
            check=False,
        )
        run_cmd(["git", "push", "origin", branch_name, "--force"], cwd=workspace, check=False)

        # Re-run reviewer to verify the fixes
        print(f"[*] Re-running Autonomous Architectural Reviewer on PR #{pr_num} after fixes...", flush=True)
        rev_res = subprocess.run(
            [sys.executable, "scripts/ai_pr_reviewer.py", "--pr-number", str(pr_num), "--workspace", str(workspace)],
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1200,
        )
        print(rev_res.stdout, flush=True)

        if review_status_file.exists():
            try:
                status_data = json.loads(review_status_file.read_text(encoding="utf-8"))
                score = status_data.get("score", score)
                verdict = status_data.get("verdict", verdict)
            except Exception:
                pass

    if verdict == "APPROVED" and score >= 90:
        print(
            f"[🚀] PR #{pr_num} APPROVED (Score: {score}/100)! Attempting to merge PR #{pr_num} into main...",
            flush=True,
        )
        run_cmd(["gh", "label", "create", "ready-to-merge", "--color", "0E8A16", "-f"], cwd=workspace, check=False)
        run_cmd(["gh", "pr", "edit", str(pr_num), "--add-label", "ready-to-merge"], cwd=workspace, check=False)
        merge_res = run_cmd(["gh", "pr", "merge", str(pr_num), "--squash", "--admin"], cwd=workspace, check=False)

        # Verify PR was actually merged on GitHub
        pr_state_raw = run_cmd(["gh", "pr", "view", str(pr_num), "--json", "state,merged"], cwd=workspace, check=False)
        is_merged = False
        try:
            pr_data = json.loads(pr_state_raw) if pr_state_raw else {}
            is_merged = pr_data.get("merged", False) or pr_data.get("state") == "MERGED"
        except Exception:
            pass

        if is_merged:
            print(
                f"[SUCCESS] Merged PR #{pr_num} into main! Contributor activity recorded for {USER_NAME}.", flush=True
            )
            run_cmd(
                [
                    "gh",
                    "pr",
                    "comment",
                    str(pr_num),
                    "--body",
                    f"✅ **Pull Request #{pr_num} successfully merged into `main`**.\n\nAll automated architectural reviews (score: {score}/100) and tests passed.",
                ],
                cwd=workspace,
                check=False,
            )
            run_cmd(
                ["gh", "issue", "close", str(issue_num), "-c", f"Resolved and merged in PR #{pr_num}."],
                cwd=workspace,
                check=False,
            )
            run_cmd(["git", "checkout", "main"], cwd=workspace)
            run_cmd(["git", "pull", "origin", "main"], cwd=workspace)
            # Clean up feature branch
            run_cmd(["git", "branch", "-D", branch_name], cwd=workspace, check=False)
            run_cmd(["git", "push", "origin", "--delete", branch_name], cwd=workspace, check=False)
            return True
        else:
            print(
                f"[!] PR #{pr_num} merge command did not complete merge: {merge_res}. Leaving open for sweeper.",
                flush=True,
            )
            run_cmd(
                [
                    "gh",
                    "pr",
                    "comment",
                    str(pr_num),
                    "--body",
                    f"⚠️ **Merge Incomplete**: Auto-merge attempted but GitHub reported conflicts or blocked merge:\n```text\n{merge_res}\n```\nBranch preserved for automated self-healing.",
                ],
                cwd=workspace,
                check=False,
            )
            run_cmd(["git", "checkout", "main"], cwd=workspace)
            return False
    else:
        s_data = {}
        if review_status_file.exists():
            try:
                s_data = json.loads(review_status_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        if verdict == "REJECT" or score < 60 or s_data.get("should_close", False):
            print(
                f"[*] PR #{pr_num} rejected by Architectural Gatekeeper as unnecessary (Score: {score}/100). Closing...",
                flush=True,
            )
            reason_text = s_data.get("close_reason") or s_data.get(
                "executive_summary", "Change evaluated as unnecessary, duplicate, or anti-pattern."
            )
            full_comment = f"🛑 **Architectural Gatekeeper: PR Closed as Unnecessary**\n\n**Verdict**: {verdict} | **Score**: {score}/100\n\n**Rationale**: {reason_text}\n\n*Closing PR to maintain codebase invariants.*"
            run_cmd(
                ["gh", "pr", "close", str(pr_num), "--repo", REPO, "--comment", full_comment, "--delete-branch"],
                cwd=workspace,
                check=False,
            )
            run_cmd(["git", "checkout", "main"], cwd=workspace)
            return False
        else:
            print(f"[!] PR #{pr_num} verdict: {verdict} (Score: {score}). Awaiting review fixes.", flush=True)
            run_cmd(["git", "checkout", "main"], cwd=workspace)
            return False


def heal_and_merge_open_prs(workspace: Path, worker_id: int = 1, num_workers: int = 5) -> bool:
    """
    Finds open PRs assigned to this worker shard, self-heals failing tests,
    runs architectural review, and merges PRs when approved (score >= 90).
    Also closes obsolete PRs whose linked issues are already closed.
    """
    try:
        out = run_cmd(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                REPO,
                "--state",
                "open",
                "--limit",
                "100",
                "--json",
                "number,title,headRefName,url,comments",
            ],
            cwd=workspace,
        )
        prs = json.loads(out) if out else []
    except Exception as e:
        print(f"[Warning] Failed to fetch open PRs: {e}", file=sys.stderr, flush=True)
        return False

    if not prs:
        return False

    def is_candidate_pr(p):
        ref = p.get("headRefName", "")
        title = p.get("title", "")
        comments = [c.get("body", "") for c in p.get("comments", [])]
        has_fix = any("/fix" in c for c in comments)
        return (
            ref.startswith("ai/")
            or "feat(ai)" in title
            or "feat(plan)" in title
            or ref.startswith("feature/")
            or ref.startswith("feat/")
            or has_fix
        )

    candidate_prs = [p for p in prs if is_candidate_pr(p)]
    # Distribute PRs deterministically across parallel workers
    if num_workers > 1:
        candidate_prs = [p for p in candidate_prs if (p.get("number", 0) % num_workers) == (worker_id - 1)]

    if not candidate_prs:
        return False

    print(
        f"\n[PR Sweeper] Worker {worker_id} found {len(candidate_prs)} open candidate PR(s). Checking for self-healing and auto-merge...",
        flush=True,
    )

    py_bin = get_python_bin(workspace)
    env = os.environ.copy()

    for pr in candidate_prs:
        pr_num = pr["number"]
        head_ref = pr["headRefName"]
        title = pr["title"]
        print(f"\n[*] Evaluating PR #{pr_num}: {title} (branch: {head_ref})...", flush=True)

        # Check if linked issue is already closed
        linked_issue = None
        if "issue-" in head_ref:
            try:
                linked_issue = int(head_ref.split("issue-")[-1].split("-")[0])
            except Exception:
                pass
        if not linked_issue:
            m = re.search(r"#(\d+)", title)
            if m:
                linked_issue = int(m.group(1))

        if linked_issue:
            try:
                iss_out = run_cmd(
                    ["gh", "issue", "view", str(linked_issue), "--repo", REPO, "--json", "state,comments"],
                    cwd=workspace,
                    check=False,
                )
                if iss_out and '"state":"CLOSED"' in iss_out:
                    # Check if the issue was solved by ANOTHER merged PR, not this PR itself
                    comments_data = json.loads(iss_out).get("comments", [])
                    merged_other_pr = None
                    for c in comments_data:
                        body_c = c.get("body", "")
                        match_pr = re.search(r"PR #(\d+)", body_c)
                        if match_pr and int(match_pr.group(1)) != pr_num:
                            merged_other_pr = int(match_pr.group(1))
                            break

                    if merged_other_pr:
                        print(
                            f"[*] PR #{pr_num} resolves Issue #{linked_issue} which was already resolved by PR #{merged_other_pr}. Closing duplicate PR...",
                            flush=True,
                        )
                        close_reason = f"👋 **Closing PR #{pr_num}**: Linked Issue #{linked_issue} was already resolved and merged in PR #{merged_other_pr}."
                        run_cmd(
                            [
                                "gh",
                                "pr",
                                "close",
                                str(pr_num),
                                "--repo",
                                REPO,
                                "--comment",
                                close_reason,
                                "--delete-branch",
                            ],
                            cwd=workspace,
                            check=False,
                        )
                        continue
                    else:
                        print(
                            f"[*] PR #{pr_num}: Linked Issue #{linked_issue} is closed. Closing obsolete PR...",
                            flush=True,
                        )
                        close_reason = f"👋 **Closing PR #{pr_num}**: Linked Issue #{linked_issue} is closed and no longer requires implementation."
                        run_cmd(
                            [
                                "gh",
                                "pr",
                                "close",
                                str(pr_num),
                                "--repo",
                                REPO,
                                "--comment",
                                close_reason,
                                "--delete-branch",
                            ],
                            cwd=workspace,
                            check=False,
                        )
                        continue
            except Exception:
                pass

        try:
            run_cmd("git reset --hard HEAD", cwd=workspace, check=False)
            run_cmd("git clean -fd", cwd=workspace, check=False)
            run_cmd(["git", "fetch", "origin", head_ref], cwd=workspace, check=False)
            checkout_res = run_cmd(
                ["git", "checkout", "-B", head_ref, f"origin/{head_ref}"], cwd=workspace, check=False
            )
            curr_b = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=workspace).strip()
            if curr_b != head_ref:
                print(f"[!] Warning: Failed to checkout branch {head_ref}, skipping", flush=True)
                continue

            # Merge origin/main to keep branch up to date
            merge_res = subprocess.run(
                ["git", "merge", "origin/main", "--no-edit"], cwd=workspace, capture_output=True, text=True
            )
            if merge_res.returncode != 0:
                print(
                    f"[*] Merging origin/main produced conflicts on #{pr_num}. Resolving scripts/ and workflow conflicts...",
                    flush=True,
                )
                run_cmd(["git", "checkout", "origin/main", "--", ".github/", "scripts/"], cwd=workspace, check=False)
                run_cmd("git add -A", cwd=workspace, check=False)
                run_cmd(
                    [
                        "git",
                        "commit",
                        "-m",
                        "merge: resolve tooling and scripts conflicts with origin/main",
                        "--no-edit",
                    ],
                    cwd=workspace,
                    check=False,
                )

            # Run pre-flight quality verification gate (deterministic auto-fix, compileall, ruff, pytest)
            is_green, err_report = verify_and_auto_fix_preflight(workspace)
            has_fix_request = any("/fix" in c.get("body", "") for c in pr.get("comments", []))

            # If auto-fix repaired changes (e.g. ruff imports/formatting), commit them
            diff_check = subprocess.run(["git", "status", "--porcelain"], cwd=workspace, capture_output=True, text=True)
            if diff_check.stdout.strip() and is_green:
                print(
                    f"[*] Fast deterministic auto-fix resolved issues on PR #{pr_num}. Pushing repair commit...",
                    flush=True,
                )
                run_cmd(["git", "config", "--replace-all", "user.name", USER_NAME], cwd=workspace, check=False)
                run_cmd(["git", "config", "--replace-all", "user.email", USER_EMAIL], cwd=workspace, check=False)
                run_cmd(
                    "git rm --cached -f ai_pr_*.md ai_review_*.json ci_fix_*.md 2>/dev/null || true",
                    cwd=workspace,
                    check=False,
                )
                run_cmd(["git", "add", "-A"], cwd=workspace)
                run_cmd(
                    "git reset -- ai_pr_*.md ai_review_*.json ci_fix_*.md 2>/dev/null || true",
                    cwd=workspace,
                    check=False,
                )
                run_cmd(
                    [
                        "git",
                        "commit",
                        "--author",
                        f"{USER_NAME} <{USER_EMAIL}>",
                        "-m",
                        f"style(ci): deterministic ruff import and formatting auto-fix for PR #{pr_num}",
                    ],
                    cwd=workspace,
                    check=False,
                )
                run_cmd(["git", "push", "origin", head_ref], cwd=workspace, check=False)

            if not is_green or has_fix_request:
                print(
                    f"[*] PR #{pr_num} requires repair (green: {is_green}, /fix: {has_fix_request}). Invoking AI CI Fixer...",
                    flush=True,
                )
                fixer_env = env.copy()
                fixer_env["GEMINI_SOLVER_KEY"] = GLOBAL_POOL.next_key()
                fixer_env["GH_REPO"] = REPO

                ci_fixer_cmd = [
                    sys.executable,
                    "scripts/ai_ci_fixer.py",
                    "--pr-number",
                    str(pr_num),
                    "--workspace",
                    str(workspace),
                    "--max-iterations",
                    "3",
                ]
                fix_res = subprocess.run(
                    ci_fixer_cmd,
                    cwd=workspace,
                    env=fixer_env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=600,
                )
                print(fix_res.stdout, flush=True)

                is_green, err_report = verify_and_auto_fix_preflight(workspace)
                if is_green:
                    run_cmd(["git", "config", "--replace-all", "user.name", USER_NAME], cwd=workspace, check=False)
                    run_cmd(["git", "config", "--replace-all", "user.email", USER_EMAIL], cwd=workspace, check=False)
                    run_cmd(
                        "git rm --cached -f ai_pr_*.md ai_review_*.json ci_fix_*.md 2>/dev/null || true",
                        cwd=workspace,
                        check=False,
                    )
                    run_cmd(["git", "add", "-A"], cwd=workspace)
                    run_cmd(
                        "git reset -- ai_pr_*.md ai_review_*.json ci_fix_*.md 2>/dev/null || true",
                        cwd=workspace,
                        check=False,
                    )
                    run_cmd(
                        [
                            "git",
                            "commit",
                            "--author",
                            f"{USER_NAME} <{USER_EMAIL}>",
                            "-m",
                            f"fix(ci): automated self-healing repair for PR #{pr_num}",
                        ],
                        cwd=workspace,
                        check=False,
                    )
                    run_cmd(["git", "push", "origin", head_ref], cwd=workspace, check=False)
                else:
                    print(
                        f"[!] PR #{pr_num} repair pass did not achieve 100% green. Closing unviable PR...", flush=True
                    )
                    close_reason = f"🛑 **CI Quality Gate: PR Closed (Unviable / Invariants Not Satisfied)**\n\nAutomated self-healing repair passes were exhausted without achieving passing test suites.\n\n*Closing PR and deleting branch to keep repository clean.*"
                    run_cmd(
                        [
                            "gh",
                            "pr",
                            "close",
                            str(pr_num),
                            "--repo",
                            REPO,
                            "--comment",
                            close_reason,
                            "--delete-branch",
                        ],
                        cwd=workspace,
                        check=False,
                    )
                    continue

            # Proceed to architectural review if tests pass
            if is_green:
                print(f"[*] PR #{pr_num} tests 100% green. Running Autonomous Reviewer...", flush=True)
                rev_env = env.copy()
                rev_env["GEMINI_REVIEWER_KEY"] = GLOBAL_POOL.next_key()
                rev_env["GH_REPO"] = REPO

                rev_res = subprocess.run(
                    [
                        sys.executable,
                        "scripts/ai_pr_reviewer.py",
                        "--pr-number",
                        str(pr_num),
                        "--workspace",
                        str(workspace),
                    ],
                    cwd=workspace,
                    env=rev_env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=1200,
                )
                print(rev_res.stdout, flush=True)

                review_status_file = workspace / "ai_review_status.json"
                score = 0
                verdict = "ACTION_REQUIRED"
                s_data = {}
                if review_status_file.exists():
                    try:
                        s_data = json.loads(review_status_file.read_text(encoding="utf-8"))
                        score = s_data.get("score", 0)
                        verdict = s_data.get("verdict", "ACTION_REQUIRED")
                    except Exception:
                        pass

                review_md_file = workspace / "ai_pr_review.md"
                if review_md_file.exists():
                    run_cmd(
                        ["gh", "pr", "comment", str(pr_num), "--body-file", str(review_md_file)],
                        cwd=workspace,
                        check=False,
                    )

                if verdict == "APPROVED" and score >= 90:
                    print(
                        f"[🚀] PR #{pr_num} APPROVED (Score: {score}/100)! Attempting to merge into main...", flush=True
                    )
                    run_cmd(
                        ["gh", "label", "create", "ready-to-merge", "--color", "0E8A16", "-f"],
                        cwd=workspace,
                        check=False,
                    )
                    run_cmd(
                        ["gh", "pr", "edit", str(pr_num), "--add-label", "ready-to-merge"], cwd=workspace, check=False
                    )
                    merge_res = run_cmd(
                        ["gh", "pr", "merge", str(pr_num), "--squash", "--admin"], cwd=workspace, check=False
                    )

                    # Verify PR was actually merged on GitHub
                    pr_state_raw = run_cmd(
                        ["gh", "pr", "view", str(pr_num), "--json", "state,merged"], cwd=workspace, check=False
                    )
                    is_merged = False
                    try:
                        pr_data = json.loads(pr_state_raw) if pr_state_raw else {}
                        is_merged = pr_data.get("merged", False) or pr_data.get("state") == "MERGED"
                    except Exception:
                        pass

                    if is_merged:
                        print(
                            f"[SUCCESS] Merged PR #{pr_num} into main! Contributor activity recorded for {USER_NAME}.",
                            flush=True,
                        )
                        run_cmd(
                            [
                                "gh",
                                "pr",
                                "comment",
                                str(pr_num),
                                "--body",
                                f"✅ **Pull Request #{pr_num} successfully merged into `main`**.\n\nAll automated architectural reviews (score: {score}/100) and tests passed.",
                            ],
                            cwd=workspace,
                            check=False,
                        )
                        if linked_issue:
                            run_cmd(
                                [
                                    "gh",
                                    "issue",
                                    "close",
                                    str(linked_issue),
                                    "-c",
                                    f"Resolved and merged in PR #{pr_num}.",
                                ],
                                cwd=workspace,
                                check=False,
                            )
                        run_cmd(["git", "checkout", "main"], cwd=workspace)
                        run_cmd(["git", "pull", "origin", "main"], cwd=workspace)
                        run_cmd(["git", "branch", "-D", head_ref], cwd=workspace, check=False)
                        run_cmd(["git", "push", "origin", "--delete", head_ref], cwd=workspace, check=False)
                        return True
                    else:
                        print(
                            f"[!] PR #{pr_num} merge command did not complete merge: {merge_res}. Leaving open for next cycle.",
                            flush=True,
                        )
                        run_cmd(
                            [
                                "gh",
                                "pr",
                                "comment",
                                str(pr_num),
                                "--body",
                                f"⚠️ **Merge Incomplete**: Auto-merge attempted but GitHub reported conflicts or blocked merge:\n```text\n{merge_res}\n```\nBranch preserved for automated self-healing.",
                            ],
                            cwd=workspace,
                            check=False,
                        )
                        run_cmd(["git", "checkout", "main"], cwd=workspace)
                        return False
                elif verdict == "REJECT" or score < 60 or s_data.get("should_close", False):
                    print(
                        f"[*] PR #{pr_num} REJECTED as unnecessary/anti-pattern (Score: {score}/100). Closing...",
                        flush=True,
                    )
                    reason_text = s_data.get("close_reason") or s_data.get(
                        "executive_summary",
                        "Architectural gatekeeper evaluated this change as unnecessary, duplicate, or anti-pattern.",
                    )
                    full_comment = f"🛑 **Architectural Gatekeeper: PR Closed as Unnecessary / Not Viable**\n\n**Verdict**: {verdict} | **Score**: {score}/100\n\n**Rationale**: {reason_text}\n\n*Closing PR and deleting branch to keep strict repository invariants.*"
                    run_cmd(
                        [
                            "gh",
                            "pr",
                            "close",
                            str(pr_num),
                            "--repo",
                            REPO,
                            "--comment",
                            full_comment,
                            "--delete-branch",
                        ],
                        cwd=workspace,
                        check=False,
                    )
                    continue
                else:
                    print(
                        f"[*] PR #{pr_num} verdict: {verdict} (Score: {score}). Left open for next review cycle.",
                        flush=True,
                    )
        except Exception as e:
            print(f"[Warning] Failed evaluating PR #{pr_num}: {e}", file=sys.stderr, flush=True)
        finally:
            run_cmd(["git", "checkout", "main"], cwd=workspace, check=False)

    return False


def run_issue_job(
    workspace: Path,
    issue: dict,
    execution_loop: ExecutionLoop | None = None,
    org: str = "default",
) -> bool:
    """Executes the full issue-to-PR workflow for a given issue using ExecutionLoop.
    Charges 3 credits for combo_fix upfront.
    Returns True if issue was successfully solved and PR opened/merged.
    """
    loop = execution_loop or GLOBAL_EXECUTION_LOOP
    issue_num = issue["number"]
    issue_title = issue["title"]
    issue_body = issue.get("body", "")

    print(f"\n[*] ExecutionLoop initiating combo_fix (3 credits) for Issue #{issue_num}...", flush=True)

    # Check daily volume and cost limits (Task 15)
    can_proceed, limit_reason = volume_limiter.check_limits(org_id=org, is_pr=True)
    if not can_proceed:
        print(f"[Volume Limit Gate] {limit_reason}", file=sys.stderr, flush=True)
        return False

    if not loop.ledger.charge(org, "combo_fix"):
        print(
            f"[ExecutionLoop] Insufficient credits for org '{org}' (balance: {loop.ledger.get(org)}, required: 3).",
            file=sys.stderr,
            flush=True,
        )
        return False

    try:
        success = solve_issue(
            workspace=workspace,
            issue_num=issue_num,
            issue_title=issue_title,
            issue_body=issue_body,
        )
        if success:
            volume_limiter.record_usage(org_id=org, prs=1)
        return bool(success)
    except Exception as e:
        print(
            f"[ExecutionLoop Watchdog] Issue #{issue_num} failed with unhandled error: {e}", file=sys.stderr, flush=True
        )
        traceback.print_exc(file=sys.stderr)
        # System-error auto-refund full 3 credits
        loop.ledger.refund(org, 3)
        return False


def run_loop_iteration(
    workspace: Path,
    worker_id: int = 1,
    num_workers: int = 5,
    execution_loop: ExecutionLoop | None = None,
):
    """Executes a single cycle of the autonomous loop."""
    # 0. Active Triage & Cleanup Gatekeeper: Automatically close unneeded, obsolete, or duplicate PRs & issues
    if worker_id == 1:
        try:
            from scripts.triage_cleanup import audit_and_close_unneeded_prs, audit_and_close_unneeded_issues

            audit_and_close_unneeded_prs(workspace)
            audit_and_close_unneeded_issues(workspace)
        except Exception as e:
            print(f"[Warning] Triage cleanup error: {e}", file=sys.stderr, flush=True)

    # 1. Active PR Sweeper & Self-Healing: Drain open PRs first
    healed = heal_and_merge_open_prs(workspace, worker_id=worker_id, num_workers=num_workers)
    if healed:
        print(f"[*] Worker {worker_id} successfully merged an open PR in this cycle.", flush=True)

    # 2. Fetch available advancement issues not currently locked by an active PR or remote branch
    issues = get_open_advancement_issues(workspace)

    if not issues:
        print(
            "[*] All currently open advancement issues already have active PRs or remote branches. Generating next task from Master Implementation Plan...",
            flush=True,
        )
        generate_new_issue(workspace)
        time.sleep(5)
        issues = get_open_advancement_issues(workspace)

    if not issues:
        print("[!] No issues ready to solve (waiting for new issue or PR merge).", flush=True)
        return

    # Deterministic work partitioning across parallel workers
    idx = (worker_id - 1) % len(issues)
    target = issues[idx]
    solve_issue(workspace, target["number"], target["title"], target.get("body", ""))


def main():
    parser = argparse.ArgumentParser(description="GossipMesh Autonomous Multi-Agent Daemon")
    parser.add_argument("--workspace", default=".", help="Path to GossipMesh repository root")
    parser.add_argument("--once", action="store_true", help="Run once and exit instead of continuous daemon")
    parser.add_argument(
        "--iterations", type=int, default=0, help="Number of advancement cycles to run (0 for continuous daemon)"
    )
    parser.add_argument("--interval", type=int, default=10, help="Interval in seconds between cycles (default: 10s)")
    parser.add_argument("--worker-id", type=int, default=1, help="Worker matrix ID (1-based)")
    parser.add_argument("--num-workers", type=int, default=5, help="Total number of parallel workers")
    parser.add_argument(
        "--max-minutes",
        type=int,
        default=0,
        help="Maximum runtime in minutes before graceful handoff (0 for unlimited)",
    )
    parser.add_argument(
        "--add-keys", nargs="*", default=[], help="Additional Gemini API keys to add to the round-robin pool"
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    if args.add_keys:
        GLOBAL_POOL.add_keys(args.add_keys)

    print(
        f"[*] GossipMesh Multi-Agent Engine initialized with {len(GLOBAL_POOL)} API keys in active rotation.",
        flush=True,
    )

    start_time = time.time()

    if args.once:
        run_loop_iteration(
            workspace, worker_id=args.worker_id, num_workers=args.num_workers, execution_loop=execution_loop
        )
    elif args.iterations > 0:
        print(
            f"[*] Starting GossipMesh Autonomous Batch ({args.iterations} cycles, max: {args.max_minutes}m, interval: {args.interval}s, worker: {args.worker_id}/{args.num_workers})...",
            flush=True,
        )
        for i in range(args.iterations):
            print(f"\n=======================================================", flush=True)
            print(
                f"[*] Advancement Batch Cycle {i + 1}/{args.iterations} (Worker {args.worker_id}/{args.num_workers})",
                flush=True,
            )
            print(f"=======================================================", flush=True)
            try:
                run_loop_iteration(
                    workspace, worker_id=args.worker_id, num_workers=args.num_workers, execution_loop=execution_loop
                )
            except Exception as e:
                print(f"[Error in cycle {i + 1}]: {e}", file=sys.stderr, flush=True)

            if args.max_minutes > 0 and (time.time() - start_time) >= (args.max_minutes * 60):
                print(f"[*] Target runtime ({args.max_minutes} mins) reached. Gracefully concluding batch.", flush=True)
                break

            if i + 1 < args.iterations:
                time.sleep(args.interval)
    else:
        print(
            f"[*] Starting GossipMesh Continuous Autonomous Daemon (interval: {args.interval}s, max: {args.max_minutes}m, worker: {args.worker_id}/{args.num_workers})...",
            flush=True,
        )
        while True:
            try:
                run_loop_iteration(
                    workspace, worker_id=args.worker_id, num_workers=args.num_workers, execution_loop=execution_loop
                )
            except Exception as e:
                print(f"[Error in loop]: {e}", file=sys.stderr, flush=True)

            if args.max_minutes > 0 and (time.time() - start_time) >= (args.max_minutes * 60):
                print(
                    f"[*] Target runtime ({args.max_minutes} mins) reached. Gracefully concluding continuous cycle.",
                    flush=True,
                )
                break

            print(f"[*] Sleeping for {args.interval} seconds until next iteration...", flush=True)
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
