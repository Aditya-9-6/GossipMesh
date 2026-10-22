"""Unit tests for GitHub permissions audit and least-privilege enforcement (Task 55)."""

import pytest
from gossipmesh.core.exceptions import AuthorizationError
from gossipmesh.integrations.github_permissions import (
    GITHUB_PERMISSION_MATRIX,
    GitHubPermissionLevel,
    GitHubPermissionsAuditor,
    GitHubResource,
)


def test_permission_matrix_integrity():
    # Verify all expected operations are mapped
    expected_ops = [
        "sync_repository",
        "read_file_contents",
        "get_pr_diff",
        "get_pr_comments",
        "create_inline_comment",
        "submit_pr_review",
        "create_pull_request",
        "create_branch_and_commit",
        "list_issues",
        "create_issue",
        "post_issue_comment",
        "create_check_run",
    ]
    for op in expected_ops:
        assert op in GITHUB_PERMISSION_MATRIX
        spec = GITHUB_PERMISSION_MATRIX[op]
        assert "resource" in spec
        assert "level" in spec
        assert "endpoint" in spec
        assert "description" in spec


def test_least_privilege_verification_success():
    # Minimum permissions manifest
    granted = {
        "metadata": "read",
        "contents": "write",
        "pull_requests": "write",
        "issues": "write",
        "checks": "write",
    }

    # All standard operations should pass
    for op in GITHUB_PERMISSION_MATRIX:
        assert GitHubPermissionsAuditor.verify_operation_permission(op, granted) is True


def test_insufficient_permission_rejection():
    read_only_granted = {
        "metadata": "read",
        "contents": "read",
        "pull_requests": "read",
        "issues": "read",
    }

    # Reading diff should succeed with read permission
    assert GitHubPermissionsAuditor.verify_operation_permission("get_pr_diff", read_only_granted) is True

    # Writing inline comments requires write permission, must fail with AuthorizationError
    with pytest.raises(AuthorizationError) as exc:
        GitHubPermissionsAuditor.verify_operation_permission("create_inline_comment", read_only_granted)
    assert "Insufficient permission" in str(exc.value.message)

    # Creating pull request requires write permission, must fail
    with pytest.raises(AuthorizationError) as exc:
        GitHubPermissionsAuditor.verify_operation_permission("create_pull_request", read_only_granted)
    assert "Insufficient permission" in str(exc.value.message)


def test_excessive_prohibited_permission_rejection():
    # If a customer or token has administration permissions, reject it as a security violation
    excessive_granted = {
        "metadata": "read",
        "pull_requests": "write",
        "administration": "write",
    }

    with pytest.raises(AuthorizationError) as exc:
        GitHubPermissionsAuditor.verify_operation_permission("get_pr_diff", excessive_granted)
    assert "Excessive permission 'administration:write' is prohibited" in str(exc.value.message)


def test_audit_app_manifest():
    # Valid manifest
    valid_manifest = {
        "metadata": "read",
        "contents": "write",
        "pull_requests": "write",
        "issues": "write",
        "checks": "write",
    }
    audit = GitHubPermissionsAuditor.audit_app_manifest(valid_manifest)
    assert audit["is_least_privilege"] is True
    assert len(audit["excessive_permissions"]) == 0
    assert len(audit["missing_permissions"]) == 0
    assert audit["supported_operations_count"] == len(GITHUB_PERMISSION_MATRIX)

    # Manifest with excessive and missing permissions
    bad_manifest = {
        "metadata": "read",
        "administration": "write",
    }
    audit_bad = GitHubPermissionsAuditor.audit_app_manifest(bad_manifest)
    assert audit_bad["is_least_privilege"] is False
    assert "administration:write" in audit_bad["excessive_permissions"]
    assert len(audit_bad["missing_permissions"]) > 0


def test_unknown_operation_raises():
    with pytest.raises(ValueError) as exc:
        GitHubPermissionsAuditor.get_required_permission("non_existent_github_op")
    assert "Unknown GitHub operation" in str(exc.value)
