"""Unit tests for Finding Normalization and Deduplication (Task 71)."""

import pytest
from gossipmesh.models.pr_review import Confidence, RemediationModel, SecurityFinding, Severity
from gossipmesh.review.normalization import (
    FindingNormalizer,
    canonicalize_path,
    canonicalize_category,
    canonicalize_severity,
    canonicalize_confidence,
    compute_stable_fingerprint,
)


def test_canonicalization_helpers():
    """Verify paths, categories, and severities are properly canonicalized."""
    assert canonicalize_path(r".\gossipmesh\core\security.py") == "gossipmesh/core/security.py"
    assert canonicalize_path("///services//auth.py") == "services/auth.py"

    assert canonicalize_category("sql-injection") == "SQL_INJECTION"
    assert canonicalize_category("secret leak") == "SECRET_LEAK"
    assert canonicalize_category("") == "SECURITY"

    assert canonicalize_severity("critical") == "CRITICAL"
    assert canonicalize_severity("UNKNOWN_SEV") == "MEDIUM"

    conf_enum, score = canonicalize_confidence("high")
    assert conf_enum == Confidence.HIGH
    assert score == 90

    conf_enum, score = canonicalize_confidence(None, confidence_score=45)
    assert conf_enum == Confidence.LOW
    assert score == 45


def test_stable_fingerprint_whitespace_invariance():
    """Verify fingerprints are stable across whitespace and formatting differences in snippet."""
    snip1 = """
        query = f"SELECT * FROM users WHERE id = {user_id}"
        cursor.execute(query)
    """
    snip2 = 'query = f"SELECT * FROM users WHERE id = {user_id}"\ncursor.execute(query)'

    fp1 = compute_stable_fingerprint("db/query.py", "SQL_INJECTION", "CWE-89", snippet=snip1)
    fp2 = compute_stable_fingerprint("db/query.py", "SQL_INJECTION", "CWE-89", snippet=snip2)
    assert fp1 == fp2

    # Different rule produces different fingerprint
    fp3 = compute_stable_fingerprint("db/query.py", "SQL_INJECTION", "CWE-20", snippet=snip1)
    assert fp1 != fp3


def test_raw_finding_normalization():
    """Verify raw dict normalization into typed SecurityFinding."""
    raw = {
        "file_path": r".\gossipmesh\api\routers\auth.py",
        "line": "42",
        "end_line": "44",
        "category": "hardcoded-secret",
        "rule_id": "SEC-004",
        "severity": "high",
        "confidence": "high",
        "message": "Potential hardcoded JWT secret key.",
        "code_snippet": "SECRET = 'supersecretkey123'",
        "remediation": {
            "description": "Load secret from environment variable",
            "auto_patch": "- SECRET = 'supersecretkey123'\n+ SECRET = os.getenv('SECRET_KEY')",
        },
        "source_scanner": "secret_scanner",
    }

    norm = FindingNormalizer.normalize_finding(raw)
    assert isinstance(norm, SecurityFinding)
    assert norm.file_path == "gossipmesh/api/routers/auth.py"
    assert norm.line == 42
    assert norm.end_line == 44
    assert norm.category == "HARDCODED_SECRET"
    assert norm.severity == "HIGH"
    assert norm.confidence == Confidence.HIGH
    assert norm.fingerprint != ""
    assert norm.evidence_structured is not None
    assert norm.evidence_structured.code_snippet == "SECRET = 'supersecretkey123'"
    assert isinstance(norm.remediation, RemediationModel)
    assert "Load secret" in norm.remediation.description


def test_inter_source_consolidation():
    """Verify that multiple scanners flagging the same issue get consolidated into one finding."""
    # Finding 1: from deterministic Bandit scanner (high severity, basic message)
    f1 = FindingNormalizer.normalize_finding(
        {
            "file_path": "gossipmesh/crypto/key.py",
            "line": 15,
            "category": "WEAK_CRYPTO",
            "rule_id": "B303",
            "severity": "HIGH",
            "confidence": "HIGH",
            "message": "Use of MD5 hash detected",
            "code_snippet": "hashlib.md5(data)",
            "source_scanner": "deterministic:bandit",
        }
    )

    # Finding 2: from AI reviewer (same code snippet & rule, medium severity, rich patch)
    f2 = FindingNormalizer.normalize_finding(
        {
            "file_path": "gossipmesh/crypto/key.py",
            "line": 15,
            "category": "WEAK_CRYPTO",
            "rule_id": "B303",
            "severity": "MEDIUM",
            "confidence": "MEDIUM",
            "message": "MD5 is cryptographically broken and vulnerable to collision attacks.",
            "code_snippet": "hashlib.md5(data)",
            "remediation": {
                "description": "Use SHA-256 instead",
                "auto_patch": "- hashlib.md5(data)\n+ hashlib.sha256(data)",
            },
            "source_scanner": "ai:gemini",
        }
    )

    assert f1.fingerprint == f2.fingerprint

    consolidated = FindingNormalizer.consolidate_findings([f1, f2])
    assert len(consolidated) == 1
    merged = consolidated[0]

    # Preserved highest severity
    assert merged.severity == "HIGH"
    # Preserved highest confidence
    assert merged.confidence == Confidence.HIGH
    # Combined sources
    assert "deterministic:bandit" in merged.sources
    assert "ai:gemini" in merged.sources
    # Preserved rich remediation
    assert isinstance(merged.remediation, RemediationModel)
    assert "hashlib.sha256" in merged.remediation.auto_patch


def test_cross_run_deduplication():
    """Verify findings already seen in prior runs/PR comments are dropped."""
    f = FindingNormalizer.normalize_finding(
        {
            "file_path": "services/auth.py",
            "line": 10,
            "category": "INSECURE_COOKIE",
            "code_snippet": "response.set_cookie(secure=False)",
            "source_scanner": "linter",
        }
    )

    seen = {f.fingerprint}
    result = FindingNormalizer.consolidate_findings([f], existing_fingerprints=seen)
    assert len(result) == 0
