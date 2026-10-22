#!/usr/bin/env python3
"""
Automates creation of GitHub issues from the Master Implementation Plan
and scaffolds minimal PRs to address each issue.
The script:
1. Parses MASTER_IMPLEMENTATION_PLAN.md and ENTERPRISE_SAAS_IMPLEMENTATION_PLAN.md
   for task identifiers (e.g. "Task 12", "Phase 3", "feat(foo.py)").
2. For each identifier:
   * If an open issue with that exact title does not exist, creates it.
   * Creates a feature branch ``task/<slug>``.
   * Adds a placeholder file ``TODO_<slug>.md`` containing the plan excerpt.
   * Commits and pushes the branch.
   * Opens a PR targeting ``main`` with a standard title and body.
   * Labels the PR with ``reviewed`` and ``score-0`` (initial score).
The script is intended to be run in a CI job (GitHub Actions) after the
PR‑review step.
"""

import re, json, subprocess, sys, os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_FILES = [
    REPO_ROOT / "docs" / "MASTER_IMPLEMENTATION_PLAN.md",
    REPO_ROOT / "docs" / "ENTERPRISE_SAAS_IMPLEMENTATION_PLAN.md",
]


def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if result.returncode != 0:
        print(f"Cmd failed ({result.returncode}): {cmd}\n{result.stderr}", file=sys.stderr)
        return ""
    return result.stdout.strip()


def slugify(txt):
    # simple safe slug for branch/file names
    txt = txt.lower()
    txt = re.sub(r"[^a-z0-9]+", "-", txt)
    return txt.strip("-")


def extract_tasks(text):
    pattern = re.compile(r"(?:Task\s*\d+|Phase\s*\d+|feat\([^\)]+\))", re.IGNORECASE)
    return {m.group(0).strip() for m in pattern.finditer(text)}


def main():
    all_tasks = set()
    for pf in PLAN_FILES:
        if pf.exists():
            all_tasks.update(extract_tasks(pf.read_text(encoding="utf-8", errors="ignore")))
    print(f"Found {len(all_tasks)} tasks in plan files.")

    # Existing open issues
    issues_json = run_cmd("gh issue list --state open --json number,title")
    open_issues = json.loads(issues_json) if issues_json else []
    issue_titles = {i["title"]: i["number"] for i in open_issues}

    for task in sorted(all_tasks):
        if task in issue_titles:
            print(f"Issue already exists for task: {task}")
            continue
        # Create issue
        print(f"Creating issue for task: {task}")
        issue_body = f"Auto‑generated from implementation plan.\n\nTask reference: **{task}**"
        run_cmd(f'gh issue create --title "{task}" --body "{issue_body}"')

        # Scaffold PR
        branch = f"task/{slugify(task)}"
        run_cmd(f"git checkout -b {branch}")
        placeholder_path = REPO_ROOT / f"TODO_{slugify(task)}.md"
        placeholder_path.write_text(f"# TODO: {task}\n\n{issue_body}\n", encoding="utf-8")
        run_cmd(f"git add {placeholder_path}")
        run_cmd(f'git commit -m "Add placeholder for {task}"')
        run_cmd(f"git push origin {branch}")
        pr_title = f"[Task] {task} – scaffold"
        pr_body = f"This PR adds a scaffold for task **{task}** extracted from the Master Implementation Plan.\n\nOnce the actual implementation is ready, replace the placeholder file with real code."
        run_cmd(f'gh pr create --title "{pr_title}" --body "{pr_body}" --head {branch} --base main')
        # Add initial labels (reviewed, score-0) – the reviewer bot will later update
        # We fetch the PR number just created (gh pr view --json number -q .number)
        pr_num = run_cmd(f"gh pr list --head {branch} --json number -q '.[0].number'")
        if pr_num:
            run_cmd(f"gh pr edit {pr_num} --add-label reviewed --add-label score-0")
        # Return to main
        run_cmd("git checkout main")


if __name__ == "__main__":
    main()
