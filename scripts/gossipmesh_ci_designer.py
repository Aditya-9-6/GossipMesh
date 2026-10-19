import os
import sys
import json
import subprocess
from pathlib import Path

# Simple CI designer for GossipMesh PRs.
# It inspects the changed files in the PR and decides which CI labels to apply.
# In a real implementation this could call a GossipMesh AI service to generate a custom workflow.


def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed: {cmd}\n{result.stderr}", file=sys.stderr)
    return result.stdout.strip()


def add_label(pr_number, label, token):
    # Ensure label exists in repository first
    run_cmd(f'gh label create "{label}" --force 2>/dev/null || true')
    cmd = f'gh pr edit {pr_number} --add-label "{label}"'
    run_cmd(cmd)
    print(f"Added label {label} to PR #{pr_number}")


def comment_pr(pr_number, comment, token):
    cmd = f'gh pr comment {pr_number} --body "{comment}"'
    run_cmd(cmd)
    print(f"Commented on PR #{pr_number}")


def get_changed_files(pr_number, token):
    # Use gh CLI to list changed files
    out = run_cmd(f"gh pr view {pr_number} --json files -q .files[].filename")
    return out.splitlines()


def decide_ci_labels(files):
    labels = []
    # Simple heuristics
    if any(f.endswith(".py") for f in files):
        labels.append("ci-python-tests")
    if any(f.endswith(".go") for f in files):
        labels.append("ci-go-tests")
    if any(f.endswith(".js") for f in files) or any(f.endswith(".ts") for f in files):
        labels.append("ci-node-tests")
    if any("Dockerfile" in f for f in files):
        labels.append("ci-docker")
    if any("Makefile" in f for f in files):
        labels.append("ci-make")
    return labels


def main():
    pr_number = os.getenv("PR_NUMBER")
    token = os.getenv("GH_TOKEN")
    if not pr_number:
        print("PR_NUMBER env var missing", file=sys.stderr)
        sys.exit(1)
    files = get_changed_files(pr_number, token)
    labels = decide_ci_labels(files)
    if not labels:
        comment = "CI Designer: No specific CI labels needed for this PR."
        comment_pr(pr_number, comment, token)
        return
    # Apply labels
    for label in labels:
        add_label(pr_number, label, token)
    # Post a summary comment
    comment = f"CI Designer has added the following CI labels based on changed files: {', '.join(labels)}."
    comment_pr(pr_number, comment, token)


if __name__ == "__main__":
    main()
