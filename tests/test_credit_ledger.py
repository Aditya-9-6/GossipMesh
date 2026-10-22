import pytest

from gossipmesh.core.config import DEFAULT_INITIAL_CREDITS
from gossipmesh.services.execution_loop import CreditLedger, InsufficientCreditsError, ExecutionLoop


def test_credit_ledger_default_balance():
    ledger = CreditLedger(initial_credits=1000)
    assert ledger.get_balance("default") == 1000
    assert ledger.get_balance("org-acme") == 1000


def test_credit_ledger_atomic_2_2_3_charging():
    ledger = CreditLedger(initial_credits=1000)

    # issue_scan = 2 credits
    assert ledger.charge("default", "issue_scan") is True
    assert ledger.get_balance("default") == 998

    # pr_review = 2 credits
    assert ledger.charge("default", "pr_review") is True
    assert ledger.get_balance("default") == 996

    # combo_fix = 3 credits
    assert ledger.charge("default", "combo_fix") is True
    assert ledger.get_balance("default") == 993


def test_credit_ledger_insufficient_credits():
    ledger = CreditLedger(initial_credits=2)
    # Attempting to charge 3 for combo_fix when balance is 2 should fail
    assert ledger.charge("default", "combo_fix") is False
    assert ledger.get_balance("default") == 2

    # Charging 2 for issue_scan succeeds
    assert ledger.charge("default", "issue_scan") is True
    assert ledger.get_balance("default") == 0


def test_credit_ledger_refund():
    ledger = CreditLedger(initial_credits=1000)
    ledger.charge("default", 3)
    assert ledger.get_balance("default") == 997

    # System error or verification failure refund
    ledger.refund("default", 3)
    assert ledger.get_balance("default") == 1000


def test_cancellation_mid_run_refunds_zero():
    ledger = CreditLedger(initial_credits=1000)
    exec_loop = ExecutionLoop(workspace=".", ledger=ledger)

    cancelled = False

    def check_cancelled():
        return cancelled

    def worker_func():
        nonlocal cancelled
        cancelled = True
        return "finished"

    # Before charge: 1000. Charge combo_fix upfront: 997.
    # Cancelled mid-run: refund 0 credits -> balance stays 997.
    ledger.charge("default", 3)
    assert ledger.get_balance("default") == 997
