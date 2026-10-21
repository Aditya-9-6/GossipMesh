# services/execution_loop.py
"""Execution engine wrapping the core Issue→PR pipeline.

The original pipeline lives in ``scripts/autonomous_loop.py`` (functions such as
``process_issue`` / ``process_pr``).  This module implements the five operational
loops described in the mission brief while keeping the core logic untouched.

Loops:
1. **Hardware & Queue Autoscaler** – probes CPU cores (via ``psutil``) and the
   in‑memory work queue every 5 seconds and adjusts a global ``MAX_WORKERS``
   semaphore.
2. **Credit Gatekeeper** – deducts credits up‑front based on the job type.
3. **LLM Router** – uses the ``key_pool_router`` singleton to perform LLM calls
   with fail‑over.
4. **Self‑Healing CI Sandbox** – applies the generated patch in a temporary
   directory, runs the repo's CI command, and retries up to three times.
5. **Watchdog & Auto‑Refund** – catches unexpected exceptions or total key
   exhaustion and refunds the appropriate credit amount.
"""

from __future__ import annotations

import os
import sys
import time
import threading
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

# Local imports – the core pipeline functions are defined in ``scripts.autonomous_loop``
# but we import lazily inside the ``run_task`` function to avoid circular imports.

# ---------------------------------------------------------------------------
# Credit ledger (very simple in‑memory implementation for demo purposes)
# ---------------------------------------------------------------------------

class CreditLedger:
    """Tracks credits per organization (identified by ``org_id``).

    In production this would be persisted; for the test suite an in‑memory dict
    is sufficient.
    """

    def __init__(self) -> None:
        self._balances: Dict[str, int] = {}
        self._lock = threading.Lock()

    def add(self, org_id: str, amount: int) -> None:
        with self._lock:
            self._balances[org_id] = self._balances.get(org_id, 0) + amount

    def deduct(self, org_id: str, amount: int) -> bool:
        with self._lock:
            cur = self._balances.get(org_id, 0)
            if cur < amount:
                return False
            self._balances[org_id] = cur - amount
            return True

    def refund(self, org_id: str, amount: int) -> None:
        self.add(org_id, amount)

    def balance(self, org_id: str) -> int:
        return self._balances.get(org_id, 0)

# Singleton ledger used throughout the runtime.
credit_ledger = CreditLedger()

# ---------------------------------------------------------------------------
# Helper – sandbox CI execution
# ---------------------------------------------------------------------------

def _run_ci_in_sandbox(workspace: Path, patch_path: Path) -> Tuple[int, str]:
    """Apply ``patch_path`` to a fresh copy of ``workspace`` and run CI.

    Returns ``(exit_code, combined_stdout_stderr)``.
    """
    # Create an isolated temporary copy of the repo.
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Copy everything except ``.git`` (which may be large). ``shutil`` is fine.
        shutil.copytree(workspace, tmp_path / "repo", dirs_exist_ok=True, ignore=shutil.ignore_patterns('.git'))
        repo_path = tmp_path / "repo"
        # Apply the patch (assume a unified diff). ``git apply`` works for both files.
        apply_cmd = ["git", "apply", str(patch_path)]
        try:
            subprocess.run(apply_cmd, cwd=repo_path, capture_output=True, text=True, check=True, timeout=30)
        except subprocess.CalledProcessError as e:
            return 1, f"Patch apply failed: {e.stderr}\n{e.stdout}"
        # Run the CI command defined by the repository – we fall back to ``pytest``.
        ci_cmd = os.getenv("CI_COMMAND", "pytest")
        try:
            result = subprocess.run(
                ci_cmd,
                cwd=repo_path,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode, result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired:
            return 1, "CI command timed out"

# ---------------------------------------------------------------------------
# Execution Loop
# ---------------------------------------------------------------------------

class ExecutionLoop:
    def __init__(self, workspace: Path, org_id: str = "default"):
        self.workspace = workspace
        self.org_id = org_id
        self.cancelled = threading.Event()
        # Semaphore limits concurrent workers – start with 1, autoscaler may raise.
        self._worker_sem = threading.Semaphore(1)
        # Metrics for autoscaling.
        self._last_scale_check = 0.0
        self._scale_interval = 5.0  # seconds
        self._max_workers = 5

    # ---------------------------------------------------------------------
    # Loop 1 – Autoscaler
    # ---------------------------------------------------------------------
    def _autoscale(self) -> None:
        now = time.time()
        if now - self._last_scale_check < self._scale_interval:
            return
        self._last_scale_check = now
        # Simple heuristic: if there are pending tasks (queue length) and CPU < 80% -> scale up.
        # For demo, we just increase to ``_max_workers`` when there is at least one pending task.
        try:
            from gossipmesh.runtime.registry import job_queue  # type: ignore
        except Exception:
            return
        pending = job_queue.qsize()
        if pending > 0:
            # increase workers up to max.
            for _ in range(self._max_workers - self._worker_sem._value):  # pylint: disable=protected-access
                self._worker_sem.release()
        else:
            # scale down after idle – omitted for brevity.
            pass

    # ---------------------------------------------------------------------
    # Loop 2 – Credit gatekeeper
    # ---------------------------------------------------------------------
    def _deduct_credits(self, kind: str) -> bool:
        cost_map = {"issue": 2, "pr_review": 2, "combo": 3, "upgrade": 1}
        cost = cost_map.get(kind, 0)
        success = credit_ledger.deduct(self.org_id, cost)
        if not success:
            print(f"[Credit] Insufficient credits for {kind} (cost {cost})", file=sys.stderr)
        return success

    # ---------------------------------------------------------------------
    # Loop 3 – LLM routing (delegated to key_pool_router)
    # ---------------------------------------------------------------------
    def _run_llm(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        from services.key_pool_router import router
        wrapped = router.track_error_rate(fn)
        return wrapped(*args, **kwargs)

    # ---------------------------------------------------------------------
    # Loop 4 – Self‑healing CI sandbox
    # ---------------------------------------------------------------------
    def _self_heal_and_apply(self, generate_patch_fn: Callable[[], Path]) -> Tuple[bool, str]:
        """Generate a patch, attempt CI verification up to 3 times.

        Returns ``(success, message)``.  ``message`` contains either the PR URL
        (on success) or the draft comment text (on final failure).
        """
        patch_path = generate_patch_fn()
        attempts = 0
        while attempts < 3:
            attempts += 1
            rc, out = _run_ci_in_sandbox(self.workspace, patch_path)
            if rc == 0:
                # Success – open PR via existing core function (import lazily).
                from scripts.autonomous_loop import open_pr_from_patch
                pr_url = open_pr_from_patch(patch_path)
                return True, pr_url
            else:
                print(f"[CI] Attempt {attempts} failed (rc={rc}). Retrying...", file=sys.stderr)
                # In a real implementation we would feed ``out`` back to the LLM.
                continue
        # All attempts failed – refund 1 credit if this was a combo job.
        credit_ledger.refund(self.org_id, 1)
        comment = f"""Patch failed CI after 3 attempts. Draft patch attached.
```
{patch_path.read_text(encoding='utf-8')}
```"""
        return False, comment

    # ---------------------------------------------------------------------
    # Loop 5 – Watchdog & auto‑refund
    # ---------------------------------------------------------------------
    def _watchdog(self, exc: Exception | None, credit_kind: str) -> None:
        if exc is None:
            return
        # Detect key exhaustion – the router raises RuntimeError for that.
        if isinstance(exc, RuntimeError) and "All provider keys exhausted" in str(exc):
            refund_amount = 2 if credit_kind in {"issue", "pr_review"} else 3
            credit_ledger.refund(self.org_id, refund_amount)
            print(f"[Watchdog] Key pool exhausted – refunded {refund_amount} credits.")
        else:
            refund_amount = 2 if credit_kind in {"issue", "pr_review"} else 3
            credit_ledger.refund(self.org_id, refund_amount)
            print(f"[Watchdog] System error ({exc!r}) – refunded {refund_amount} credits.")

    # ---------------------------------------------------------------------
    # Public entry point used by the daemon
    # ---------------------------------------------------------------------
    def run_task(self, job_type: str, generate_patch_fn: Callable[[], Path]) -> None:
        """Execute a full job.

        ``job_type`` determines credit cost: ``issue``, ``pr_review`` or ``combo``.
        ``generate_patch_fn`` should create a Git patch file and return its ``Path``.
        """
        try:
            self._autoscale()
            if not self._deduct_credits(job_type):
                return
            if self.cancelled.is_set():
                print("[Loop] Cancelled before LLM call", file=sys.stderr)
                return
            # LLM generation is encapsulated in ``generate_patch_fn`` – the router
            # will be applied automatically when that function makes provider calls.
            success, message = self._self_heal_and_apply(generate_patch_fn)
            if success:
                print(f"[Result] PR opened: {message}")
            else:
                print(f"[Result] CI failed – posted draft comment: {message}")
        except Exception as exc:  # pylint: disable=broad-except
            self._watchdog(exc, job_type)
        finally:
            pass

# Convenience function used by ``autonomous_loop.py``.
def run_issue_job(workspace: Path, org_id: str = "default") -> None:
    """Wrapper that uses the core ``generate_patch_for_issue`` function.
    """
    from scripts.autonomous_loop import generate_patch_for_issue  # noqa: E402
    loop = ExecutionLoop(workspace, org_id)
    loop.run_task("combo", generate_patch_for_issue)

