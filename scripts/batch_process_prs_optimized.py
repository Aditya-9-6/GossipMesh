#!/usr/bin/env python3
"""Optimized batch processor for GossipMesh PRs.

- Determines the current GitHub core rate‑limit remaining via `gh api`.
- Sets a safe worker count (max 5) based on the remaining quota.
- Uses a ThreadPoolExecutor to run `ai_pr_reviewer.py` concurrently on
  multiple PRs, dramatically reducing wall‑clock time while staying
  well below the API limits.
- Prints a concise summary at the end.
"""

import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEWER = REPO_ROOT / "scripts" / "ai_pr_reviewer.py"

if not REVIEWER.is_file():
    sys.stderr.write(f"Reviewer script not found: {REVIEWER}\n")
    sys.exit(1)


def get_open_pr_numbers():
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--state", "open", "--json", "number", "--jq", ".[].number"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"Failed to list PRs: {e}\n{e.stderr}\n")
        sys.exit(1)


def get_remaining_rate_limit():
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
        # If we cannot fetch, fall back to a safe default.
        return 5000


def run_reviewer(pr_number):
    try:
        subprocess.run(
            [sys.executable, str(REVIEWER), "--pr-number", pr_number],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return (pr_number, "OK")
    except subprocess.CalledProcessError as e:
        return (pr_number, f"FAIL: {e}")


def main():
    pr_numbers = get_open_pr_numbers()
    if not pr_numbers:
        print("No open PRs found.")
        return

    remaining = get_remaining_rate_limit()
    # Reserve some headroom; assume each PR may consume ~30 core requests.
    safe_workers = max(1, min(5, remaining // 30))
    print(f"GitHub core remaining: {remaining}, using {safe_workers} concurrent worker(s).")
    print(f"Processing {len(pr_numbers)} PR(s)...")

    results = []
    with ThreadPoolExecutor(max_workers=safe_workers) as executor:
        future_to_pr = {executor.submit(run_reviewer, pr): pr for pr in pr_numbers}
        for future in as_completed(future_to_pr):
            pr = future_to_pr[future]
            try:
                pr_id, status = future.result()
                results.append((pr_id, status))
                print(f"PR #{pr_id}: {status}")
            except Exception as exc:
                results.append((pr, f"EXCEPTION: {exc}"))
                print(f"PR #{pr}: EXCEPTION {exc}")

    ok = sum(1 for _, s in results if s == "OK")
    fail = len(results) - ok
    print(f"\nDone. {ok} succeeded, {fail} failed.")


if __name__ == "__main__":
    main()
