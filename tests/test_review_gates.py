"""Unit tests for Deterministic Review Gates (Task 72)."""

import pytest
from gossipmesh.models.pr_review import SecurityFinding, TestResult, Verdict
from gossipmesh.review.gates import (
    ASTSecurityScanner,
    ChangedFilePolicyScanner,
    DependencyScanner,
    DeterministicReviewGates,
    SecretScanner,
)
from gossipmesh.review.prompt_pipeline import ChangedFileContext


def test_secret_scanner_detects_credentials():
    """Verify secret scanner detects AWS keys, Slack webhooks, and private keys."""
    slack_url = "https://" + "hooks." + "slack.com/services/" + "T12345678/B12345678/123456789012345678901234"
    file = ChangedFileContext(
        path="gossipmesh/config.py",
        patch=f"""
+ AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
+ SLACK_URL = "{slack_url}"
+ PRIVATE = "-----BEGIN RSA PRIVATE KEY-----"
        """,
    )

    findings = SecretScanner.scan(file)
    assert len(findings) >= 3
    rule_ids = {f.rule_id for f in findings}
    assert "AWS_KEY" in rule_ids
    assert "SLACK_WEBHOOK" in rule_ids
    assert "PRIVATE_KEY" in rule_ids
    assert all(f.severity == "CRITICAL" for f in findings)


def test_dependency_scanner_flags_banned_packages():
    """Verify dependency scanner detects banned packages in requirements.txt."""
    req_file = ChangedFileContext(
        path="requirements.txt",
        patch="""
+ fastapi==0.109.0
+ telnetlib3==2.0.4
+ pycrypto==2.6.1
        """,
    )

    findings = DependencyScanner.scan(req_file)
    assert len(findings) == 2
    messages = " ".join(f.message for f in findings)
    assert "telnetlib3" in messages
    assert "pycrypto" in messages


def test_ast_security_scanner_detects_dangerous_calls():
    """Verify AST scanner detects eval(), exec(), and os.system()."""
    py_file = ChangedFileContext(
        path="gossipmesh/dynamic.py",
        patch="""
+ def execute_user_code(code_str):
+     eval(code_str)
+     exec(code_str)
        """,
    )

    findings = ASTSecurityScanner.scan(py_file)
    assert len(findings) >= 2
    assert any("eval" in f.message for f in findings)
    assert any("exec" in f.message for f in findings)


def test_changed_file_policy_flags_protected_files():
    """Verify policy scanner rejects modifications to .github/workflows and alembic migrations."""
    wf_file = ChangedFileContext(
        path=".github/workflows/deploy.yml",
        patch="+ run: echo 'deploying'",
    )
    findings = ChangedFilePolicyScanner.scan(wf_file)
    assert len(findings) == 1
    assert "PROTECTED_WORKFLOW" in findings[0].rule_id

    mig_file = ChangedFileContext(
        path="alembic/versions/12345_critical.py",
        patch="+ op.drop_table('users')",
    )
    findings = ChangedFilePolicyScanner.scan(mig_file)
    assert len(findings) == 1
    assert "MIGRATION_CHANGE" in findings[0].rule_id


def test_deterministic_gates_verdict_logic():
    """Verify aggregate verdict logic based on finding severities and test results."""
    gates = DeterministicReviewGates()

    # Case 1: Clean files and passing tests -> APPROVE
    clean_file = ChangedFileContext(
        path="gossipmesh/services/calc.py",
        patch="+ def square(x): return x * x",
    )
    tests_passing = [TestResult(status="passed", test_id="test_calc", name="test_square", passed=True)]
    verdict, score, findings = gates.evaluate(files=[clean_file], test_results=tests_passing)
    assert verdict == Verdict.APPROVE
    assert score >= 90
    assert len(findings) == 0

    # Case 2: Critical finding -> REJECT
    slack_url = "https://" + "hooks." + "slack.com/services/" + "T12345678/B12345678/123456789012345678901234"
    leaky_file = ChangedFileContext(
        path="gossipmesh/api.py",
        patch=f'+ SLACK_HOOK = "{slack_url}"',
    )
    verdict, score, findings = gates.evaluate(files=[leaky_file], test_results=tests_passing)
    assert verdict == Verdict.REJECT
    assert score <= 50
    assert any(f.severity == "CRITICAL" for f in findings)

    # Case 3: Test failure -> REQUEST_CHANGES
    failing_tests = [TestResult(status="failed", test_id="test_calc", name="test_square", passed=False, error_message="AssertionError")]
    verdict, score, findings = gates.evaluate(files=[clean_file], test_results=failing_tests)
    assert verdict == Verdict.REQUEST_CHANGES
    assert score <= 70
    assert any(f.rule_id == "FAILING_TESTS" for f in findings)
