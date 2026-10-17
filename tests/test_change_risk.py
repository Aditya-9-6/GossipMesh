import pytest
from gossipmesh.enterprise.risk_classifier import ChangeRiskClassifier, ChangeDetails, RiskLevel

def test_low_risk_classification():
    classifier = ChangeRiskClassifier()
    details = ChangeDetails(
        files_changed=["gossipmesh/utils.py"],
        additions=10,
        deletions=2,
        has_tests=True
    )
    result = classifier.classify(details)
    assert result.risk_level == RiskLevel.LOW
    assert result.requires_approval is False
    assert result.blocked is False

def test_medium_risk_classification():
    classifier = ChangeRiskClassifier()
    details = ChangeDetails(
        files_changed=["gossipmesh/api/routers/users.py"],
        additions=120,
        deletions=40,
        has_dependencies_change=True
    )
    result = classifier.classify(details)
    assert result.risk_level == RiskLevel.MEDIUM
    assert result.requires_approval is True
    assert result.blocked is False

def test_high_risk_classification():
    classifier = ChangeRiskClassifier()
    details = ChangeDetails(
        files_changed=["gossipmesh/auth/authorization.py", "alembic/versions/123_migration.py"],
        additions=600,
        deletions=100,
        has_auth_change=True,
        has_migrations=True
    )
    result = classifier.classify(details)
    assert result.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    assert result.requires_approval is True

def test_critical_risk_classification():
    classifier = ChangeRiskClassifier()
    details = ChangeDetails(
        files_changed=[f"gossipmesh/auth/file_{i}.py" for i in range(10)],
        additions=3000,
        deletions=500,
        has_auth_change=True,
        has_migrations=True
    )
    result = classifier.classify(details)
    assert result.risk_level == RiskLevel.CRITICAL
    assert result.blocked is True
    assert result.requires_approval is True
