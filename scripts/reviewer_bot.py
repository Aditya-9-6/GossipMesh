# Reviewer Bot for PRs
# This script is a placeholder that performs a simple evaluation of a PR.
# It calculates a dummy "score" based on number of changed files and adds a comment.
# It also adds a label "reviewed" to the PR.

import subprocess
import json
import os
import sys

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed: {cmd}\n{result.stderr}", file=sys.stderr)
    return result.stdout.strip()

def main():
    pr_number = os.getenv("PR_NUMBER")
    if not pr_number:
        print("PR_NUMBER env var not set", file=sys.stderr)
        sys.exit(1)
    # Get PR details
    pr_json = run_cmd(f"gh pr view {pr_number} --json number,title,headRefName,baseRefName,changedFiles,additions,deletions,mergeable")
    pr = json.loads(pr_json)
    # Simple scoring: fewer changes = higher score
    changed = pr.get("changedFiles", 0)
    additions = pr.get("additions", 0)
    deletions = pr.get("deletions", 0)
    score = max(0, 100 - (changed * 2 + additions + deletions) // 10)
    # Post a comment
    comment = f"🧠 **Reviewer Bot**\nScore: **{score}** / 100\n\n_This is an automated evaluation based on change size._"
    run_cmd(f"gh pr comment {pr_number} --body \"{comment}\"")
    # Add labels
    run_cmd(f"gh pr edit {pr_number} --add-label reviewed --add-label score-{score}")
    print(f"Reviewed PR #{pr_number} with score {score}")

if __name__ == "__main__":
    main()
