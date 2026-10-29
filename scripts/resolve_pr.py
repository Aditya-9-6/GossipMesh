#!/usr/bin/env python3
"""
Autonomous PR Conflict Resolver for GossipMesh.
Sanitizes carriage-return corrupted Git tree objects, removes G: paths,
merges origin/main, and pushes clean mergeable branches.
"""

import sys
import subprocess
import json


def run_cmd(cmd, check=True, text=True, input=None):
    return subprocess.run(cmd, check=check, capture_output=True, text=text, input=input)


def clean_tree(tree_sha: str) -> str:
    """Recursively strips trailing carriage return from directory/file names and drops G: entries."""
    res = subprocess.run(["git", "ls-tree", "-z", tree_sha], capture_output=True, check=True)
    raw = res.stdout
    if not raw:
        return tree_sha
    if b"\r" not in raw and b"G:" not in raw:
        return tree_sha

    entries = []
    for chunk in raw.split(b"\0"):
        if not chunk:
            continue
        meta, name = chunk.split(b"\t", 1)
        mode, obj_type, sha = meta.split(b" ")
        clean_name = name.rstrip(b"\r")
        if clean_name.startswith(b"G:") or clean_name == b"G" or clean_name == b".gossip_mesh":
            continue

        if obj_type == b"tree":
            clean_sub = clean_tree(sha.decode())
            entries.append(f"{mode.decode()} tree {clean_sub}\t{clean_name.decode()}\0".encode("utf-8"))
        else:
            entries.append(f"{mode.decode()} blob {sha.decode()}\t{clean_name.decode()}\0".encode("utf-8"))

    mktree = subprocess.run(["git", "mktree", "-z"], input=b"".join(entries), capture_output=True, check=True)
    return mktree.stdout.decode().strip()


def sanitize_branch(branch_name: str) -> str:
    """Rebuilds branch commit with sanitized clean tree without checking out."""
    head_sha = run_cmd(["git", "rev-parse", branch_name]).stdout.strip()
    tree_sha = run_cmd(["git", "rev-parse", f"{head_sha}^{{tree}}"]).stdout.strip()
    clean_root = clean_tree(tree_sha)
    if clean_root != tree_sha:
        print(f"[*] Pruned corrupted entries from tree {tree_sha} -> {clean_root}")
        commit_res = run_cmd(
            [
                "git",
                "commit-tree",
                clean_root,
                "-p",
                head_sha,
                "-m",
                "fix(repo): strip carriage returns and G: drive from git tree objects\n\nCo-authored-by: Dahale Aditya Dnyaneshwar <adityadahale96@gmail.com>",
            ]
        )
        new_commit = commit_res.stdout.strip()
        run_cmd(["git", "update-ref", f"refs/heads/{branch_name}", new_commit])
        return new_commit
    return head_sha


def fetch_and_prepare_branch(head_ref: str, local_branch: str):
    # Clean previous local branch if exists
    run_cmd(["git", "branch", "-D", local_branch], check=False)

    # Fetch branch
    print(f"[*] Fetching origin/{head_ref}...")
    run_cmd(["git", "fetch", "origin", f"{head_ref}:{local_branch}"])

    # Sanitize tree
    print(f"[*] Sanitizing Git tree...")
    sanitize_branch(local_branch)

    # Checkout
    print(f"[*] Checking out {local_branch}...")
    run_cmd(["git", "checkout", local_branch])


def merge_main_and_resolve_conflicts(pr_number: int) -> bool:
    # Merge origin/main
    print(f"[*] Merging origin/main...")
    merge_res = subprocess.run(
        ["git", "merge", "origin/main", "-m", f"merge origin/main into PR #{pr_number} [resolve conflicts]"],
        capture_output=True,
        text=True,
    )

    if merge_res.returncode != 0:
        print(f"[!] Conflict encountered during merge:\n{merge_res.stdout}\n{merge_res.stderr}")
        # Check conflicted files
        conflicted_files = [
            line.strip()
            for line in run_cmd(["git", "diff", "--name-only", "--diff-filter=U"]).stdout.splitlines()
            if line.strip()
        ]
        print(f"[!] Conflicted files: {conflicted_files}")

        for cf in conflicted_files:
            print(f"[*] Resolving {cf}...")
            chk = subprocess.run(["git", "cat-file", "-e", f"origin/main:{cf}"], capture_output=True)
            if chk.returncode == 0:
                print(f"    Restoring {cf} from origin/main...")
                run_cmd(["git", "checkout", "origin/main", "--", cf])
                run_cmd(["git", "add", cf])
            else:
                print(f"    Removing {cf} (not present in origin/main)...")
                run_cmd(["git", "rm", "-f", cf], check=False)

        # Check if conflicts resolved
        unresolved = [
            line.strip()
            for line in run_cmd(["git", "diff", "--name-only", "--diff-filter=U"]).stdout.splitlines()
            if line.strip()
        ]
        if unresolved:
            print(f"[!] Still unresolved: {unresolved}")
            run_cmd(["git", "merge", "--abort"], check=False)
            run_cmd(["git", "checkout", "main"])
            return False

        run_cmd(
            [
                "git",
                "commit",
                "-m",
                f"merge origin/main into PR #{pr_number} [resolve conflicts]",
                "-m",
                "Co-authored-by: Dahale Aditya Dnyaneshwar <adityadahale96@gmail.com>",
            ]
        )
    return True


def push_branch(local_branch: str, head_ref: str):
    print(f"[*] Pushing resolved branch to origin {head_ref}...")
    push_res = run_cmd(["git", "push", "origin", f"{local_branch}:{head_ref}"])
    print(f"[OK] Pushed: {push_res.stdout.strip()}")


def check_pr_mergeable_status(pr_number: int) -> bool:
    view_res = run_cmd(["gh", "pr", "view", str(pr_number), "--json", "mergeable,title"])
    pr_data = json.loads(view_res.stdout)
    print(f"[STATUS] PR #{pr_number} mergeable: {pr_data.get('mergeable')}")
    return pr_data.get("mergeable") == "MERGEABLE"


def resolve_pr(pr_number: int, head_ref: str):
    print(f"\n==========================================")
    print(f"[*] Resolving PR #{pr_number} (Branch: {head_ref})")
    print(f"==========================================")

    local_branch = f"resolve-pr-{pr_number}"

    fetch_and_prepare_branch(head_ref, local_branch)

    if not merge_main_and_resolve_conflicts(pr_number):
        return False

    push_branch(local_branch, head_ref)

    is_mergeable = check_pr_mergeable_status(pr_number)

    run_cmd(["git", "checkout", "main"])
    return is_mergeable


if __name__ == "__main__":
    if len(sys.argv) > 2:
        pr_num = int(sys.argv[1])
        head_ref = sys.argv[2]
        resolve_pr(pr_num, head_ref)
    else:
        print("Usage: python scripts/resolve_pr.py <pr_number> <head_ref>")
