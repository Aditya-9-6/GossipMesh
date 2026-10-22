import io
import sys
import pytest

from gossipmesh.services.execution_loop import (
    ExecutionLoop,
    CreditLedger,
    InsufficientCreditsError,
)
from gossipmesh.services.key_pool_router import KeyPoolRouter


def test_execution_loop_worker_concurrency():
    loop = ExecutionLoop(workspace=".")
    assert loop.worker_cap >= 1


def test_execution_loop_run_task_success():
    ledger = CreditLedger(initial_credits=1000)
    router = KeyPoolRouter(initial_keys=["test-key-1"])
    loop = ExecutionLoop(workspace=".", ledger=ledger, router=router)

    def simple_add(a: int, b: int, api_key: str = ""):
        return a + b

    res = loop.run_task(simple_add, 5, 10, action="combo_fix", org="default")
    assert res == 15
    # combo_fix charges 3 credits: 1000 -> 997
    assert ledger.get_balance("default") == 997


def test_execution_loop_watchdog_auto_refund_on_error():
    ledger = CreditLedger(initial_credits=1000)
    router = KeyPoolRouter(initial_keys=["test-key-1"])
    loop = ExecutionLoop(workspace=".", ledger=ledger, router=router)

    def crashing_task():
        raise ValueError("Critical worker failure")

    # Capture stderr to verify loud watchdog output
    stderr_buf = io.StringIO()
    original_stderr = sys.stderr
    sys.stderr = stderr_buf
    try:
        with pytest.raises(ValueError):
            loop.run_task(crashing_task, action="combo_fix", org="default")
    finally:
        sys.stderr = original_stderr

    # Loud watchdog must log error and traceback
    logged_output = stderr_buf.getvalue()
    assert "Unhandled exception in task" in logged_output
    assert "ValueError: Critical worker failure" in logged_output

    # System-error auto-refund: credits should be refunded back from 997 -> 1000
    assert ledger.get_balance("default") == 1000


def test_execution_loop_sandbox_verification():
    loop = ExecutionLoop(workspace=".")
    # Empty or None test_cmd must return True by default (non-destructive)
    assert loop.sandbox_verify(None) is True
    assert loop.sandbox_verify("") is True
    assert loop.sandbox_verify("   ") is True

    # Successful command
    assert loop.sandbox_verify("python -c \"print('ok')\"") is True

    # Failing command
    assert loop.sandbox_verify('python -c "import sys; sys.exit(1)"') is False


def test_execution_loop_verification_failure_partial_refund():
    ledger = CreditLedger(initial_credits=1000)
    loop = ExecutionLoop(workspace=".", ledger=ledger)

    # Initial combo_fix charge: 3 credits
    ledger.charge("default", "combo_fix")
    assert ledger.get_balance("default") == 997

    # If verification fails after 3 passes, refund 1 credit (net cost = 2)
    loop.handle_verification_failure("default", "combo_fix")
    assert ledger.get_balance("default") == 998
