"""GitHub permissions audit, least-privilege enforcement, and permission matrix (Task 55).

Enforces that every GitHub API operation invoked by GossipMesh uses the minimum
required permission level, adhering strictly to the principle of least privilege.
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
from gossipmesh.core.exceptions import AuthorizationError


class GitHubPermissionLevel(str, Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class GitHubResource(str, Enum):
    CONTENTS = "contents"
    PULL_REQUESTS = "pull_requests"
    ISSUES = "issues"
    CHECKS = "checks"
    STATUSES = "statuses"
    METADATA = "metadata"
    MEMBERS = "members"
    ADMINISTRATION = "administration"


# Minimum Required Permission Matrix for all GossipMesh operations
# Structure: {operation_name: {resource: minimum_required_level, "endpoint": ..., "description": ...}}
GITHUB_PERMISSION_MATRIX: Dict[str, Dict[str, Any]] = {
    "sync_repository": {
        "resource": GitHubResource.METADATA,
        "level": GitHubPermissionLevel.READ,
        "endpoint": "GET /repos/{owner}/{repo}",
        "description": "Fetch repository metadata, default branch, and visibility.",
    },
    "read_file_contents": {
        "resource": GitHubResource.CONTENTS,
        "level": GitHubPermissionLevel.READ,
        "endpoint": "GET /repos/{owner}/{repo}/contents/{path}",
        "description": "Read source code files for symbol analysis, AST parsing, and indexing.",
    },
    "get_pr_diff": {
        "resource": GitHubResource.PULL_REQUESTS,
        "level": GitHubPermissionLevel.READ,
        "endpoint": "GET /repos/{owner}/{repo}/pulls/{pull_number}",
        "description": "Fetch unified diff and changed files for PR review.",
    },
    "get_pr_comments": {
        "resource": GitHubResource.PULL_REQUESTS,
        "level": GitHubPermissionLevel.READ,
        "endpoint": "GET /repos/{owner}/{repo}/pulls/{pull_number}/comments",
        "description": "Retrieve existing review comments to prevent duplicate notifications.",
    },
    "create_inline_comment": {
        "resource": GitHubResource.PULL_REQUESTS,
        "level": GitHubPermissionLevel.WRITE,
        "endpoint": "POST /repos/{owner}/{repo}/pulls/{pull_number}/comments",
        "description": "Post code-specific inline security and quality review comments.",
    },
    "submit_pr_review": {
        "resource": GitHubResource.PULL_REQUESTS,
        "level": GitHubPermissionLevel.WRITE,
        "endpoint": "POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews",
        "description": "Submit top-level summary review with status (COMMENT, REQUEST_CHANGES, APPROVE).",
    },
    "create_pull_request": {
        "resource": GitHubResource.PULL_REQUESTS,
        "level": GitHubPermissionLevel.WRITE,
        "endpoint": "POST /repos/{owner}/{repo}/pulls",
        "description": "Create automated bugfix or refactoring Pull Requests.",
    },
    "create_branch_and_commit": {
        "resource": GitHubResource.CONTENTS,
        "level": GitHubPermissionLevel.WRITE,
        "endpoint": "POST /repos/{owner}/{repo}/git/refs, PUT /repos/{owner}/{repo}/contents/{path}",
        "description": "Push autonomous bugfix commits to non-default working branches.",
    },
    "list_issues": {
        "resource": GitHubResource.ISSUES,
        "level": GitHubPermissionLevel.READ,
        "endpoint": "GET /repos/{owner}/{repo}/issues",
        "description": "List repository issues for autonomous triage and resolution.",
    },
    "create_issue": {
        "resource": GitHubResource.ISSUES,
        "level": GitHubPermissionLevel.WRITE,
        "endpoint": "POST /repos/{owner}/{repo}/issues",
        "description": "Create automated tracking issues for detected security findings or regressions.",
    },
    "post_issue_comment": {
        "resource": GitHubResource.ISSUES,
        "level": GitHubPermissionLevel.WRITE,
        "endpoint": "POST /repos/{owner}/{repo}/issues/{issue_number}/comments",
        "description": "Post progress updates and triage findings to issues.",
    },
    "create_check_run": {
        "resource": GitHubResource.CHECKS,
        "level": GitHubPermissionLevel.WRITE,
        "endpoint": "POST /repos/{owner}/{repo}/check-runs",
        "description": "Report verification suite test and lint outcomes to PR checks.",
    },
}

# Strictly forbidden / prohibited permissions (never requested or permitted in production)
FORBIDDEN_PERMISSIONS: Set[GitHubResource] = {
    GitHubResource.ADMINISTRATION,
}


class GitHubPermissionsAuditor:
    """Audits granted GitHub App or OAuth tokens against least-privilege policies."""

    @staticmethod
    def get_required_permission(operation: str) -> Tuple[GitHubResource, GitHubPermissionLevel]:
        spec = GITHUB_PERMISSION_MATRIX.get(operation)
        if not spec:
            raise ValueError(f"Unknown GitHub operation '{operation}' not defined in permission matrix.")
        return spec["resource"], spec["level"]

    @classmethod
    def verify_operation_permission(cls, operation: str, granted_permissions: Dict[str, str]) -> bool:
        """Verifies that the granted permissions satisfy the minimum requirement for the operation without granting excessive forbidden privileges."""
        # 1. Check for prohibited permissions
        for forbidden in FORBIDDEN_PERMISSIONS:
            level = granted_permissions.get(forbidden.value, "none")
            if level in ("write", "admin"):
                raise AuthorizationError(
                    message=f"Security violation: Excessive permission '{forbidden.value}:{level}' is prohibited."
                )

        # 2. Check operation requirement
        res, min_level = cls.get_required_permission(operation)
        granted_level = granted_permissions.get(res.value, "none")

        level_order = {"none": 0, "read": 1, "write": 2, "admin": 3}
        if level_order.get(granted_level, 0) < level_order.get(min_level.value, 0):
            raise AuthorizationError(
                message=f"Insufficient permission for operation '{operation}': requires '{res.value}:{min_level.value}', but only '{res.value}:{granted_level}' was granted."
            )

        return True

    @classmethod
    def audit_app_manifest(cls, manifest_permissions: Dict[str, str]) -> Dict[str, Any]:
        """Audits a GitHub App permissions manifest for least-privilege compliance."""
        excessive = []
        missing = []
        compliant_ops = []

        # Check for forbidden permissions
        for forbidden in FORBIDDEN_PERMISSIONS:
            if manifest_permissions.get(forbidden.value, "none") not in ("none", None):
                excessive.append(f"{forbidden.value}:{manifest_permissions.get(forbidden.value)}")

        # Check required ops
        for op, spec in GITHUB_PERMISSION_MATRIX.items():
            res = spec["resource"].value
            min_lvl = spec["level"].value
            granted = manifest_permissions.get(res, "none")
            level_order = {"none": 0, "read": 1, "write": 2, "admin": 3}
            if level_order.get(granted, 0) >= level_order.get(min_lvl, 0):
                compliant_ops.append(op)
            else:
                missing.append(f"{op} requires {res}:{min_lvl}")

        return {
            "is_least_privilege": len(excessive) == 0,
            "excessive_permissions": excessive,
            "missing_permissions": missing,
            "supported_operations_count": len(compliant_ops),
            "total_operations_count": len(GITHUB_PERMISSION_MATRIX),
        }
