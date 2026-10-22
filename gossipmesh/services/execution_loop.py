import os
import subprocess
import sys
import threading
import time
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from gossipmesh.core.config import DEFAULT_INITIAL_CREDITS
from gossipmesh.services.key_pool_router import (
    KeyPoolRouter,
    router as default_router,
    track_error_rate,
)

# Optional psutil import for hardware autoscaling (fallback if unavailable)
try:
    import psutil
except Exception:
    psutil = None


def calc_worker_concurrency() -> int:
    """Loop 1: Hardware & Queue Autoscaler.
    Calculates safe worker concurrency based on CPU and memory utilization.
    Guarantees at least 1 worker, defaulting to 2 if psutil is not installed.
    """
    if psutil:
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory().percent
            load = max(cpu, mem)
            # Aim for safe utilization: each worker consumes ~20-25% capacity
            workers = max(1, int((100 - load) / 25))
            return min(8, workers)
        except Exception:
            pass
    return 2


class InsufficientCreditsError(Exception):
    """Raised when an organization has insufficient credits for an action."""

    pass


class CreditLedger:
    """Loop 2: Atomic 2-2-3 Credit Gatekeeper.
    Thread-safe ledger managing organization balances.
    Action costs:
      - issue_scan: 2 credits
      - pr_review: 2 credits
      - combo_fix: 3 credits
    """

    ACTION_COSTS: dict[str, int] = {
        "issue_scan": 2,
        "pr_review": 2,
        "combo_fix": 3,
    }

    def __init__(self, initial_credits: int = DEFAULT_INITIAL_CREDITS):
        self.lock = threading.Lock()
        self.default_initial = initial_credits
        self.balances: dict[str, int] = defaultdict(lambda: self.default_initial)

    def get_balance(self, org: str = "default") -> int:
        with self.lock:
            return self.balances[org]

    def get(self, org: str = "default") -> int:
        return self.get_balance(org)

    def has_credits(self, org: str, amount_or_action: int | str) -> bool:
        amount = self.ACTION_COSTS.get(amount_or_action, 2) if isinstance(amount_or_action, str) else amount_or_action
        with self.lock:
            return self.balances[org] >= amount

    def charge(self, org: str = "default", amount_or_action: int | str = 2) -> bool:
        """Deduct credits upfront. Returns True on success, False if insufficient."""
        amount = self.ACTION_COSTS.get(amount_or_action, 2) if isinstance(amount_or_action, str) else amount_or_action
        with self.lock:
            current = self.balances[org]
            if current < amount:
                return False
            self.balances[org] = current - amount
            return True

    def refund(self, org: str = "default", amount: int = 2):
        """Add credits back to org balance."""
        with self.lock:
            self.balances[org] += amount


class ExecutionLoop:
    """The 5-Loop Execution Engine for GossipMesh:
    1. Hardware & Queue Autoscaler
    2. Atomic 2-2-3 Credit Gatekeeper
    3. Multi-Key LLM Execution
    4. Non-Destructive Sandbox Verification
    5. Loud Watchdog & System-Error Auto-Refund
    """

    def __init__(
        self,
        workspace: str | Path = ".",
        ledger: CreditLedger | None = None,
        router: KeyPoolRouter | None = None,
    ):
        self.workspace = Path(workspace).resolve()
        self.ledger = ledger or CreditLedger()
        self.router = router or default_router
        self.worker_cap = calc_worker_concurrency()

    def run_task(
        self,
        func: Callable[..., Any],
        *args,
        action: str | int = 2,
        org: str = "default",
        is_cancelled: Callable[[], bool] | None = None,
        **kwargs,
    ) -> Any:
        """Executes a task through the complete 5-loop execution lifecycle:
        - Cancellation check (refunds 0 if cancelled mid-run)
        - Upfront credit deduction (2-2-3 rules)
        - LLM execution with automatic key rotation and retry
        - Loud Watchdog with full traceback logging and auto-refund on failure
        """
        # Cancellation check before charge
        if is_cancelled and is_cancelled():
            print("[ExecutionLoop] Task cancelled before execution.", flush=True)
            return None

        # Determine credit cost
        cost = self.ledger.ACTION_COSTS.get(action, 2) if isinstance(action, str) else int(action)

        if not self.ledger.charge(org, cost):
            raise InsufficientCreditsError(
                f"Insufficient credits for org '{org}' to perform action '{action}' (required: {cost}, balance: {self.ledger.get(org)})"
            )

        # Mid-run cancellation check (0 refund if cancelled mid-run)
        if is_cancelled and is_cancelled():
            print("[ExecutionLoop] Task cancelled mid-run. Refunding 0 credits.", flush=True)
            return None

        # Loop 3 & Loop 5: LLM Execution wrapped in Watchdog and Key Pool Router
        try:
            wrapped_func = track_error_rate(func, router_instance=self.router)
            result = wrapped_func(*args, **kwargs)
            return result
        except Exception as e:
            # Loop 5: Loud Watchdog & System-Error Auto-Refund
            print(
                f"[ExecutionLoop Watchdog] Unhandled exception in task '{getattr(func, '__name__', str(func))}': {e}",
                file=sys.stderr,
                flush=True,
            )
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()

            # Fully refund credits on system failure
            self.ledger.refund(org, cost)
            raise

    def sandbox_verify(self, test_cmd: str | None = None) -> bool:
        """Loop 4: Non-Destructive Sandbox Verification.
        If test_cmd is empty/None, defaults to True to allow autonomous_loop.py
        to perform its internal quality gate directly without blocking valid PRs.
        """
        if not test_cmd or not test_cmd.strip():
            return True

        try:
            res = subprocess.run(
                test_cmd,
                shell=True,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if res.returncode != 0:
                print(f"[Sandbox Verification Failure]:\n{res.stderr or res.stdout}", file=sys.stderr, flush=True)
                return False
            return True
        except Exception as e:
            print(f"[Sandbox Verification Exception]: {e}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            return False

    def handle_verification_failure(self, org: str = "default", action: str = "combo_fix"):
        """If a 3-credit combo_fix fails verification after 3 attempts, refund 1 credit
        (charging the 2-credit issue scan rate).
        """
        if action == "combo_fix":
            self.ledger.refund(org, 1)

    def watchdog(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Direct watchdog wrapper that logs traceback and refunds 2 credits on error."""
        try:
            return func(*args, **kwargs)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self.ledger.refund("default", 2)
            raise
