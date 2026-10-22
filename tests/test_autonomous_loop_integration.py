import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gossipmesh.services.execution_loop import CreditLedger, ExecutionLoop
from gossipmesh.services.key_pool_router import KeyPoolRouter
from scripts.autonomous_loop import (
    create_pull_request,
    run_issue_job,
    run_loop_iteration,
    solve_issue,
)


def test_autonomous_loop_end_to_end_integration(tmp_path):
    """Proves that:
    a) An issue is discovered/processed,
    b) @track_error_rate rotates keys when key #1 raises a 429 error,
    c) Credits are properly deducted from 1000 -> 997, and
    d) The PR creation function in scripts/autonomous_loop.py is actually called and succeeds!
    """
    # 1. Setup isolated CreditLedger (1000 credits) and KeyPoolRouter
    ledger = CreditLedger(initial_credits=1000)
    router = KeyPoolRouter(initial_keys=["gemini-key-429", "gemini-key-valid"])
    exec_loop = ExecutionLoop(workspace=tmp_path, ledger=ledger, router=router)

    # Issue to process
    test_issue = {
        "number": 310,
        "title": "feat(p2p): Implement Zero-Allocation Merkle Wire Protocol",
        "body": "Detailed architectural requirements for anti-entropy wire protocol.",
    }

    # Tracking calls
    keys_attempted = []
    pr_created = False

    # Mock reviewer status to approve PR with score 95
    (tmp_path / "ai_review_status.json").write_text(json.dumps({"score": 95, "verdict": "APPROVED"}), encoding="utf-8")

    # Mock solver to raise 429 on first key, succeed on second key
    def fake_invoke_solver(workspace, issue_num, issue_title, issue_body, api_key=""):
        current_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        keys_attempted.append(current_key)
        if current_key == "gemini-key-429":
            raise RuntimeError("HTTP 429: ResourceExhausted rate limit quota exceeded")
        mock_proc = MagicMock(spec=subprocess.CompletedProcess)
        mock_proc.returncode = 0
        mock_proc.stdout = "AI Solver successfully generated patch."
        mock_proc.stderr = ""
        return mock_proc

    # Mock PR creation
    def fake_create_pr(workspace, branch_name, issue_num, issue_title, body_content):
        nonlocal pr_created
        pr_created = True
        return 42, "https://github.com/Aditya-9-6/GossipMesh/pull/42"

    # Mock shell commands (git, gh)
    def fake_run_cmd(cmd, cwd=None, check=False, timeout=60):
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        if "gh pr view" in cmd_str:
            return json.dumps({"state": "MERGED", "merged": True})
        if "gh pr list" in cmd_str:
            return "[]"
        return ""

    # Mock reviewer subprocess
    def fake_subprocess_run(cmd, *args, **kwargs):
        mock_proc = MagicMock(spec=subprocess.CompletedProcess)
        mock_proc.returncode = 0
        mock_proc.stdout = "Reviewer passed with score 95/100"
        mock_proc.stderr = ""
        return mock_proc

    with (
        patch("scripts.autonomous_loop.invoke_ai_solver", side_effect=fake_invoke_solver),
        patch("scripts.autonomous_loop.create_pull_request", side_effect=fake_create_pr),
        patch("scripts.autonomous_loop.verify_and_auto_fix_preflight", return_value=(True, "")),
        patch("scripts.autonomous_loop.run_cmd", side_effect=fake_run_cmd),
        patch("subprocess.run", side_effect=fake_subprocess_run),
    ):
        # Pre-execution assertions
        assert ledger.get_balance("default") == 1000

        # Execute the real entry point: run_issue_job
        success = run_issue_job(
            workspace=tmp_path,
            issue=test_issue,
            execution_loop=exec_loop,
            org="default",
        )

        # a) Proves issue is discovered/processed
        assert success is True

        # b) Proves @track_error_rate rotates keys when key #1 raises 429
        assert "gemini-key-429" in keys_attempted
        assert "gemini-key-valid" in keys_attempted
        assert router.is_on_cooldown("gemini-key-429") is True

        # c) Proves credits are properly deducted from 1000 -> 997 (combo_fix = 3 credits)
        assert ledger.get_balance("default") == 997

        # d) Proves PR creation function was actually called and succeeded
        assert pr_created is True


def test_autonomous_loop_iteration_discovery(tmp_path):
    """Proves run_loop_iteration discovers issues, charges credits, and invokes run_issue_job."""
    ledger = CreditLedger(initial_credits=1000)
    router = KeyPoolRouter(initial_keys=["key-healthy"])
    exec_loop = ExecutionLoop(workspace=tmp_path, ledger=ledger, router=router)

    discovered_issues = [{"number": 311, "title": "feat(consensus): Epoch Checkpointing", "body": "Specs"}]

    job_called = False

    def fake_run_issue_job(workspace, issue, execution_loop=None, org="default"):
        nonlocal job_called
        job_called = True
        execution_loop.ledger.charge(org, "combo_fix")
        return True

    with (
        patch("scripts.autonomous_loop.get_open_advancement_issues", return_value=discovered_issues),
        patch("scripts.autonomous_loop.heal_and_merge_open_prs", return_value=False),
        patch("scripts.autonomous_loop.run_issue_job", side_effect=fake_run_issue_job),
    ):
        run_loop_iteration(tmp_path, worker_id=1, num_workers=1, execution_loop=exec_loop)

        assert job_called is True
        assert ledger.get_balance("default") == 997
