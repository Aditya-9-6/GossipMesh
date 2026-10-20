#!/usr/bin/env python3
"""
Autonomous Triage & Cleanup Gatekeeper for GossipMesh.
High-speed batch auditing of open Pull Requests and Issues:
- Closes PRs that are obsolete, duplicate, unneeded, unviable, or whose linked issues are already closed.
- Closes Issues that are duplicates, already implemented on main, or superseded by merged PRs.
- Automatically deletes associated remote branches upon closing PRs.
"""

import sys
import os
import re
import json
import subprocess
from pathlib import Path

REPO = "Aditya-9-6/GossipMesh"


def run_cmd(cmd, cwd=None, check=False):
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd,
            shell=isinstance(cmd, str),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if check and res.returncode != 0:
            return ""
        return res.stdout.strip()
    except Exception:
        return ""


def audit_and_close_unneeded_prs(workspace: Path) -> int:
    """Audits open PRs and closes those that are not needed using fast batch queries."""
    print("[*] Fetching open PRs, closed issues, and merged PRs for batch triage...", flush=True)

    # 1. Fast batch fetch open PRs
    prs_raw = run_cmd(
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
            "number,title,headRefName,url",
        ],
        cwd=workspace,
    )
    if not prs_raw:
        print("[*] No open PRs found.", flush=True)
        return 0

    prs = json.loads(prs_raw)

    # 2. Fast batch fetch closed issue numbers
    closed_issues_raw = run_cmd(
        ["gh", "issue", "list", "--repo", REPO, "--state", "closed", "--limit", "100", "--json", "number"],
        cwd=workspace,
    )
    closed_issues = set(i["number"] for i in json.loads(closed_issues_raw)) if closed_issues_raw else set()

    # 3. Fast batch fetch merged PR numbers and linked issue references
    merged_prs_raw = run_cmd(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            REPO,
            "--state",
            "merged",
            "--limit",
            "100",
            "--json",
            "number,title,headRefName",
        ],
        cwd=workspace,
    )
    merged_prs = json.loads(merged_prs_raw) if merged_prs_raw else []

    merged_issue_to_pr = {}
    for m in merged_prs:
        t = m.get("title", "")
        h = m.get("headRefName", "")
        m_num = m.get("number")
        for num_str in re.findall(r"#(\d+)", t):
            merged_issue_to_pr[int(num_str)] = m_num
        if "issue-" in h:
            try:
                merged_issue_to_pr[int(h.split("issue-")[-1].split("-")[0])] = m_num
            except Exception:
                pass

    closed_count = 0
    issue_to_prs = {}

    for p in prs:
        num = p["number"]
        head = p["headRefName"]
        title = p["title"]
        linked = None
        if "issue-" in head:
            try:
                linked = int(head.split("issue-")[-1].split("-")[0])
            except Exception:
                pass
        if not linked:
            m = re.search(r"#(\d+)", title)
            if m:
                linked = int(m.group(1))
        p["linked_issue"] = linked
        if linked:
            issue_to_prs.setdefault(linked, []).append(p)

    for p in prs:
        num = p["number"]
        head = p["headRefName"]
        title = p["title"]
        linked = p.get("linked_issue")

        # Check 1: Linked issue was already resolved in a merged PR
        if linked and linked in merged_issue_to_pr and merged_issue_to_pr[linked] != num:
            solver_pr = merged_issue_to_pr[linked]
            reason = f"👋 **Closing PR #{num}**: Linked Issue #{linked} was already resolved and merged into `main` in PR #{solver_pr}."
            print(f"[*] Closing redundant PR #{num} (Issue #{linked} merged in PR #{solver_pr})...", flush=True)
            run_cmd(
                ["gh", "pr", "close", str(num), "--repo", REPO, "--comment", reason, "--delete-branch"], cwd=workspace
            )
            closed_count += 1
            continue

        # Check 2: Linked issue is marked CLOSED
        if linked and linked in closed_issues:
            reason = f"👋 **Closing PR #{num}**: Linked Issue #{linked} is closed and no longer planned."
            print(f"[*] Closing obsolete PR #{num} (Linked Issue #{linked} is closed)...", flush=True)
            run_cmd(
                ["gh", "pr", "close", str(num), "--repo", REPO, "--comment", reason, "--delete-branch"], cwd=workspace
            )
            closed_count += 1
            continue

        # Check 3: Duplicate PRs for the same issue (keep newest, close older ones)
        if linked and len(issue_to_prs.get(linked, [])) > 1:
            all_for_issue = sorted(issue_to_prs[linked], key=lambda x: x["number"], reverse=True)
            newest = all_for_issue[0]
            if num != newest["number"]:
                reason = f"👋 **Closing PR #{num} as duplicate**: Superseded by newer PR #{newest['number']} for Issue #{linked}."
                print(f"[*] Closing duplicate PR #{num} in favor of newer PR #{newest['number']}...", flush=True)
                run_cmd(
                    ["gh", "pr", "close", str(num), "--repo", REPO, "--comment", reason, "--delete-branch"],
                    cwd=workspace,
                )
                closed_count += 1
                continue

    print(f"[+] PR Audit Complete: Closed {closed_count} unneeded / duplicate PR(s).", flush=True)
    return closed_count


def audit_and_close_unneeded_issues(workspace: Path) -> int:
    """Audits open issues and closes those that are already resolved, duplicate, or unneeded."""
    print("[*] Auditing open Issues for necessity and validity...", flush=True)
    raw = run_cmd(
        ["gh", "issue", "list", "--repo", REPO, "--state", "open", "--limit", "100", "--json", "number,title,body"],
        cwd=workspace,
    )
    if not raw:
        print("[*] No open issues found.", flush=True)
        return 0

    issues = json.loads(raw)
    closed_count = 0

    # Fetch recently merged PRs to identify resolved issues
    prs_raw = run_cmd(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            REPO,
            "--state",
            "merged",
            "--limit",
            "100",
            "--json",
            "number,title,headRefName",
        ],
        cwd=workspace,
    )
    merged_prs = json.loads(prs_raw) if prs_raw else []

    merged_issue_to_pr = {}
    for m in merged_prs:
        t = m.get("title", "")
        h = m.get("headRefName", "")
        m_num = m.get("number")
        for num_str in re.findall(r"#(\d+)", t):
            merged_issue_to_pr[int(num_str)] = m_num
        if "issue-" in h:
            try:
                merged_issue_to_pr[int(h.split("issue-")[-1].split("-")[0])] = m_num
            except Exception:
                pass

    seen_normalized_titles = {}

    for iss in issues:
        num = iss["number"]
        title = iss["title"]

        # 1. Check if already solved in a merged PR
        if num in merged_issue_to_pr:
            solver_pr = merged_issue_to_pr[num]
            reason = f"✅ **Closing Issue #{num}**: This issue has already been resolved and merged into `main` via PR #{solver_pr}."
            print(f"[*] Closing Issue #{num}: Already resolved in merged PR #{solver_pr}.", flush=True)
            run_cmd(["gh", "issue", "close", str(num), "--repo", REPO, "--comment", reason], cwd=workspace)
            closed_count += 1
            continue

        # 2. Check for duplicate issue titles
        norm = re.sub(r"[^a-zA-Z0-9]", "", title.lower())
        if norm in seen_normalized_titles:
            primary = seen_normalized_titles[norm]
            reason = f"👋 **Closing Issue #{num} as duplicate**: Identical capability is already tracked in Issue #{primary}."
            print(f"[*] Closing duplicate Issue #{num} in favor of #{primary}...", flush=True)
            run_cmd(
                ["gh", "issue", "close", str(num), "--repo", REPO, "--reason", "not_planned", "--comment", reason],
                cwd=workspace,
            )
            closed_count += 1
            continue
        else:
            seen_normalized_titles[norm] = num

        # 3. Check for capabilities already fully present in main
        if "Adaptive Gossip Fanout" in title and (workspace / "gossipmesh" / "p2p" / "fanout.py").exists():
            reason = f"✅ **Closing Issue #{num}**: Adaptive Gossip Fanout Control is already fully implemented on `main` in `gossipmesh/p2p/fanout.py`."
            print(f"[*] Closing Issue #{num}: Capability already present on main.", flush=True)
            run_cmd(["gh", "issue", "close", str(num), "--repo", REPO, "--comment", reason], cwd=workspace)
            closed_count += 1
            continue

        if "Noise Protocol Framework" in title and (workspace / "gossipmesh" / "crypto" / "noise.py").exists():
            reason = f"✅ **Closing Issue #{num}**: Noise Protocol Handshake is already fully implemented on `main` in `gossipmesh/crypto/noise.py`."
            print(f"[*] Closing Issue #{num}: Capability already present on main.", flush=True)
            run_cmd(["gh", "issue", "close", str(num), "--repo", REPO, "--comment", reason], cwd=workspace)
            closed_count += 1
            continue

    print(f"[+] Issue Audit Complete: Closed {closed_count} unneeded / duplicate issue(s).", flush=True)
    return closed_count


def main():
    workspace = Path(".").resolve()
    print("=" * 70)
    print("      GossipMesh Autonomous Triage & Cleanup Gatekeeper")
    print("=" * 70)
    prs_closed = audit_and_close_unneeded_prs(workspace)
    issues_closed = audit_and_close_unneeded_issues(workspace)
    print("=" * 70)
    print(f"[Summary] Closed {prs_closed} unneeded PR(s) and {issues_closed} unneeded Issue(s).")
    print("=" * 70)


if __name__ == "__main__":
    main()
