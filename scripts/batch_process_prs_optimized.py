#!/usr/bin/env python3
"""Optimized batch processor for GossipMesh PRs.

- Determines the current GitHub core rate‑limit remaining via `gh api`.
- Sets a safe worker count based on the remaining quota and available tasks.
- Uses a ThreadPoolExecutor to run `ai_pr_reviewer.py` concurrently on
  multiple PRs, dramatically reducing wall‑clock time while staying
  well below the API limits.
- Supports any target repository via --repo / GH_REPO.
- Distributes work across all configured AI providers.
- Prints a concise summary at the end.
"""

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEWER = REPO_ROOT / "scripts" / "ai_pr_reviewer.py"

if not REVIEWER.is_file():
    sys.stderr.write(f"Reviewer script not found: {REVIEWER}\n")
    sys.exit(1)


def get_open_pr_numbers(repo: str = None) -> list[str]:
    cmd = ["gh", "pr", "list", "--state", "open", "--json", "number", "--jq", ".[].number"]
    if repo:
        cmd.extend(["--repo", repo])
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Failed to list PRs: {e}\n{e.stderr}\n")
        return []


def get_remaining_rate_limit() -> int:
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                "-H",
                "Accept: application/vnd.github+json",
                "/rate_limit",
                "--jq",
                ".resources.core.remaining",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return int(result.stdout.strip())
    except Exception:
        return 5000


def run_reviewer(pr_number: str, repo: str = None, workspace: str = None):
    cmd = [sys.executable, str(REVIEWER), "--pr-number", str(pr_number)]
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
            timeout=360,
        )
        if res.returncode == 0:
            return (pr_number, "OK", "")
        return (pr_number, f"FAIL (exit {res.returncode})", res.stderr[-300:] if res.stderr else "")
    except Exception as e:
        return (pr_number, f"EXCEPTION: {e}", str(e))


def main():
    parser = argparse.ArgumentParser(description="GossipMesh Multi-Worker 24/7 PR Batch Processor")
    parser.add_argument(
        "--repo",
        default=os.environ.get("GH_REPO") or os.environ.get("GITHUB_REPOSITORY"),
        help="Target GitHub repository (e.g. Aditya-9-6/DevProxy)",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace directory",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Number of concurrent workers (0 = auto-calculate based on quota & PR count)",
    )
    args = parser.parse_args()

    target_repo = args.repo
    print(f"[*] Target repository: {target_repo or 'Current Repository'}")

    pr_numbers = get_open_pr_numbers(target_repo)
    if not pr_numbers:
        print("[*] No open PRs found to review.")
        return

    remaining = get_remaining_rate_limit()
    if args.workers > 0:
        safe_workers = args.workers
    else:
        # Scale workers up to 8 based on rate limits and PR load
        safe_workers = max(1, min(8, len(pr_numbers), max(1, remaining // 40)))

    print(f"[*] GitHub API core quota remaining: {remaining}")
    print(f"[*] Launching {safe_workers} parallel AI review worker(s) across {len(pr_numbers)} open PR(s)...")

    results = []
    with ThreadPoolExecutor(max_workers=safe_workers) as executor:
        future_to_pr = {executor.submit(run_reviewer, pr, target_repo, args.workspace): pr for pr in pr_numbers}
        for future in as_completed(future_to_pr):
            pr = future_to_pr[future]
            try:
                pr_id, status, err_details = future.result()
                results.append((pr_id, status))
                print(f"[>] PR #{pr_id}: {status}")
                if err_details:
                    print(f"    Details: {err_details.strip()}")
            except Exception as exc:
                results.append((pr, f"EXCEPTION: {exc}"))
                print(f"[!] PR #{pr}: EXCEPTION {exc}")

    ok = sum(1 for _, s in results if s == "OK")
    fail = len(results) - ok
    print(f"\n[✓] Batch complete: {ok} succeeded, {fail} failed out of {len(results)} PR(s).")


if __name__ == "__main__":
    main()
