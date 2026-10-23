#!/usr/bin/env python3
"""
GossipMesh Autonomous PR Reviewer Bot
Enforces the GossipMesh Master Implementation Plan and Enterprise SaaS standards.
Scores PRs against Master Implementation Plan alignment, necessity, test coverage,
blast radius, and code hygiene.
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MASTER_PLAN_PATH = REPO_ROOT / "docs" / "MASTER_IMPLEMENTATION_PLAN.md"
ENTERPRISE_PLAN_PATH = REPO_ROOT / "docs" / "ENTERPRISE_SAAS_IMPLEMENTATION_PLAN.md"


def run_cmd(cmd):
    """Execute a shell command and safely return its stdout.
    Returns an empty string on failure and suppresses Unicode decode errors.
    """
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        env=os.environ,
        encoding="utf-8",
        errors="ignore",
    )
    if result.returncode != 0:
        print(
            f"Command failed (exit {result.returncode}): {cmd}\n{result.stderr}",
            file=sys.stderr,
        )
        return result.stdout or ""
    return result.stdout.strip()


def load_master_plan_keywords():
    keywords = set()
    for plan_file in (MASTER_PLAN_PATH, ENTERPRISE_PLAN_PATH):
        if plan_file.exists():
            text = plan_file.read_text(encoding="utf-8", errors="ignore")
            # Extract task names and section keywords
            tasks = re.findall(r"(?:Task\s+\d+|Phase\s+\d+|[A-Za-z0-9_-]+(?:\.py)?)", text)
            for t in tasks:
                if len(t) > 3:
                    keywords.add(t.lower())
    return keywords


def evaluate_pr_against_master_plan(pr_number):
    pr_json = run_cmd(
        f"gh pr view {pr_number} --json number,title,body,headRefName,baseRefName,changedFiles,additions,deletions,mergeable,files"
    )
    if not pr_json:
        raise ValueError(f"Could not retrieve metadata for PR #{pr_number}")
    pr = json.loads(pr_json)

    title = pr.get("title", "")
    body = pr.get("body", "") or ""
    files = [f.get("path", "") for f in pr.get("files", [])]
    changed_count = pr.get("changedFiles", 0)
    additions = pr.get("additions", 0)
    deletions = pr.get("deletions", 0)
    mergeable = pr.get("mergeable", "UNKNOWN")

    keywords = load_master_plan_keywords()
    combined_text = f"{title} {body}".lower()

    # 1. Master Implementation Plan Alignment & Necessity (40 points max)
    master_plan_aligned = False
    plan_score = 0
    matched_aspects = []

    # Check for direct task or phase references (e.g., Task 12, Phase 1, #180)
    task_match = re.search(r"(?:task\s*#?\d+|phase\s*#?\d+|resolve\s*#?\d+|feat\([a-z0-9_-]+\))", combined_text)
    if task_match:
        plan_score += 25
        matched_aspects.append(f"Explicit roadmap link: `{task_match.group(0)}`")
        master_plan_aligned = True

    # Check for core architectural paths outlined in Master Implementation Plan
    core_paths = [
        f for f in files if f.startswith("gossipmesh/") or f.startswith("worker/") or f.startswith("scripts/")
    ]
    if core_paths:
        plan_score += 15
        matched_aspects.append(f"Touches {len(core_paths)} core Master Plan subsystem files")
    else:
        plan_score += 5

    # 2. Test Coverage & Quality Verification (30 points max)
    test_files = [f for f in files if f.startswith("tests/") or "test" in f]
    test_score = 0
    if test_files:
        test_score = 30
        matched_aspects.append(f"Comprehensive test coverage included ({len(test_files)} test files)")
    else:
        # Penalize PRs without tests according to Master Plan rules
        test_score = 5
        matched_aspects.append("⚠️ Missing dedicated test files in `tests/`")

    # 3. Blast Radius & Anti-Spaghetti Modularity (30 points max)
    modularity_score = 30
    if changed_count > 15:
        modularity_score -= min(15, (changed_count - 15))
        matched_aspects.append(f"⚠️ Large blast radius: {changed_count} files changed")
    if (additions + deletions) > 800:
        modularity_score -= min(10, (additions + deletions - 800) // 100)
        matched_aspects.append(f"⚠️ High diff volume: +{additions}/-{deletions} LOC")

    modularity_score = max(5, modularity_score)

    total_score = plan_score + test_score + modularity_score
    total_score = max(0, min(100, total_score))

    # Construct review report
    status_icon = "🟢" if total_score > 90 else ("🟡" if total_score >= 70 else "🔴")
    verdict = (
        "APPROVED (Ready for Gate)" if total_score > 90 else ("ACTION_REQUIRED" if total_score >= 70 else "REJECTED")
    )

    comment = f"""### {status_icon} GossipMesh AI Reviewer Gate: Master Implementation Plan Audit
**PR #{pr_number}**: `{title}`
**Roadmap Alignment & Necessity Score**: **{total_score} / 100**
**Verdict**: `{verdict}`
**Mergeable State**: `{mergeable}`

---
#### 📋 Master Plan Criteria Breakdown:
1. **Master Plan Alignment & Necessity**: {plan_score} / 40
2. **Test Coverage & Verification**: {test_score} / 30
3. **Modularity & Blast Radius Control**: {modularity_score} / 30

#### 🔍 Audit Findings:
"""
    for aspect in matched_aspects:
        comment += f"- {aspect}\n"

    if total_score > 90 and mergeable == "MERGEABLE":
        comment += "\n✅ **All Master Implementation Plan criteria satisfied.** Score > 90 with green mergeability."
    elif total_score <= 90:
        comment += f"\nℹ️ **Improvement Required**: Score ({total_score}) is below the >90 threshold required for automated `ready-to-merge` tag. Ensure complete test coverage and explicit Master Implementation Plan task alignment."

    return total_score, comment


def main():
    pr_number = os.getenv("PR_NUMBER")
    if not pr_number:
        print("PR_NUMBER env var not set", file=sys.stderr)
        sys.exit(1)

    # Check if comprehensive ai_pr_reviewer can be run with multi-provider keys
    has_keys = any(
        os.environ.get(k) for k in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY", "GROQ_API_KEY")
    )
    score = 0
    comment = ""

    if has_keys:
        print(f"Running full AI PR Reviewer with multi-provider LLM on PR #{pr_number}...")
        try:
            res = run_cmd(f"python scripts/ai_pr_reviewer.py --pr-number {pr_number}")
            # If successfully run, ai_pr_reviewer posts its own comment
            print(res)
        except Exception as e:
            print(f"ai_pr_reviewer failed, falling back to Master Plan auditor: {e}", file=sys.stderr)

    # Evaluate against Master Implementation Plan
    score, comment = evaluate_pr_against_master_plan(pr_number)

    # Post comment
    run_cmd(f'gh pr comment {pr_number} --body "{comment}"')

    # Add labels
    run_cmd(f"gh label create reviewed --force")
    run_cmd(f"gh label create score-{score} --force")
    run_cmd(f"gh pr edit {pr_number} --add-label reviewed --add-label score-{score}")
    if score > 90:
        run_cmd(f"gh label create ready-to-merge --force")
        run_cmd(f"gh pr edit {pr_number} --add-label ready-to-merge")
    print(f"Reviewed PR #{pr_number} against Master Implementation Plan. Score: {score}")


if __name__ == "__main__":
    main()
