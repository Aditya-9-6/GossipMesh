import pytest
from gossipmesh.change_risk import ChangeRiskClassifier, ChangeDetails, RiskLevel

def test_low_risk_classification():
    classifier = ChangeRiskClassifier()
    details = ChangeDetails(
        file_count=2,
        line_count=30,
        files_changed=["gossipmesh/utils.py"],
        has_test_changes=True
    )
    assessment = classifier.classify(details)
    assert assessment.risk_level == RiskLevel.LOW
    assert not assessment.requires_approval
    assert not assessment.is_blocked

def test_medium_risk_classification():
    classifier = ChangeRiskClassifier()
    details = ChangeDetails(
        file_count=3,
        line_count=120,
        files_changed=["pyproject.toml"],
        has_dependency_updates=True
    )
    assessment = classifier.classify(details)
    assert assessment.risk_level == RiskLevel.MEDIUM
    assert assessment.requires_approval
    assert not assessment.is_blocked

def test_high_risk_classification():
    classifier = ChangeRiskClassifier()
    details = ChangeDetails(
        file_count=4,
        line_count=80,
        files_changed=["gossipmesh/auth/authorization.py"],
        has_auth_changes=True,
        has_migrations=True
    )
    assessment = classifier.classify(details)
    assert assessment.risk_level == RiskLevel.HIGH
    assert assessment.requires_approval

def test_critical_risk_classification():
    classifier = ChangeRiskClassifier()
    details = ChangeDetails(
        file_count=60,
        line_count=3000,
        files_changed=["gossipmesh/security/crypto.py"],
        has_security_code=True,
        has_auth_changes=True
    )
    assessment = classifier.classify(details)
    assert assessment.risk_level == RiskLevel.CRITICAL
    assert assessment.requires_approval
    assert assessment.is_blocked
