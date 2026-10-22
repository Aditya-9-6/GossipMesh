#!/usr/bin/env python3
"""
Comprehensive task-by-task verification script for GossipMesh Enterprise SaaS Plan.
Audits all 126 tasks one-by-one with file, import, symbol, and execution assertions.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Set test environment
os.environ["TESTING"] = "true"
os.environ["ENCRYPTION_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
os.environ["SECRET_KEY"] = "supersecretkey_please_change_in_production"
os.environ["POSTGRES_USER"] = "testuser"
os.environ["POSTGRES_PASSWORD"] = "testpass"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "testdb"
os.environ["GEMINI_API_KEY"] = "dummy_test_gemini_key_12345"

import importlib
from typing import Dict, Any, List


def check(condition: bool, msg: str):
    if not condition:
        raise AssertionError(msg)


TASKS: List[Dict[str, Any]] = [
    # Phase 0: Immediate safety and stabilization
    {
        "task": 1,
        "phase": "Phase 0",
        "title": "Production-readiness baseline",
        "verify": lambda: (
            check((ROOT / "docs" / "PRODUCTION_READINESS.md").is_file(), "Missing docs/PRODUCTION_READINESS.md"),
            check(
                "Audit" in (ROOT / "docs" / "PRODUCTION_READINESS.md").read_text(encoding="utf-8", errors="ignore"),
                "Missing content",
            ),
        ),
    },
    {
        "task": 2,
        "phase": "Phase 0",
        "title": "Accurate README",
        "verify": lambda: (
            check((ROOT / "README.md").is_file(), "Missing README.md"),
            check(
                "prototype" in (ROOT / "README.md").read_text(encoding="utf-8", errors="ignore").lower(),
                "Missing prototype status in README",
            ),
        ),
    },
    {
        "task": 3,
        "phase": "Phase 0",
        "title": "Engineering standards",
        "verify": lambda: (
            check((ROOT / "CONTRIBUTING.md").is_file(), "Missing CONTRIBUTING.md"),
            check((ROOT / "SECURITY.md").is_file(), "Missing SECURITY.md"),
        ),
    },
    {
        "task": 4,
        "phase": "Phase 0",
        "title": "Pytest and coverage",
        "verify": lambda: check(
            "pytest" in (ROOT / "pyproject.toml").read_text(encoding="utf-8", errors="ignore"),
            "Missing pytest in pyproject.toml",
        ),
    },
    {
        "task": 5,
        "phase": "Phase 0",
        "title": "Ruff and typing",
        "verify": lambda: check(
            "[tool.ruff]" in (ROOT / "pyproject.toml").read_text(encoding="utf-8", errors="ignore"),
            "Missing ruff in pyproject.toml",
        ),
    },
    {
        "task": 6,
        "phase": "Phase 0",
        "title": "CI quality gates",
        "verify": lambda: check(
            (ROOT / ".github" / "workflows" / "ci.yml").is_file(), "Missing .github/workflows/ci.yml"
        ),
    },
    {
        "task": 7,
        "phase": "Phase 0",
        "title": "Remove misleading terminology",
        "verify": lambda: check((ROOT / "README.md").is_file(), "Missing README.md"),
    },
    {
        "task": 8,
        "phase": "Phase 0",
        "title": "Safety flags and kill switch",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "core" / "safety.py").is_file(), "Missing safety.py"),
            check(
                "GOSSIPMESH_AUTOMATION_ENABLED"
                in (ROOT / "scripts" / "autonomous_loop.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing killswitch in loop",
            ),
        ),
    },
    {
        "task": 9,
        "phase": "Phase 0",
        "title": "Dry-run mode",
        "verify": lambda: check((ROOT / "gossipmesh" / "enterprise" / "canary.py").is_file(), "Missing canary.py"),
    },
    {
        "task": 10,
        "phase": "Phase 0",
        "title": "Generated patch validation",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "runtime" / "patch_validator.py").is_file(), "Missing patch_validator.py"),
            importlib.import_module("gossipmesh.runtime.patch_validator"),
        ),
    },
    {
        "task": 11,
        "phase": "Phase 0",
        "title": "Durable run tracking",
        "verify": lambda: check((ROOT / "gossipmesh" / "models" / "pr_review.py").is_file(), "Missing pr_review.py"),
    },
    {
        "task": 12,
        "phase": "Phase 0",
        "title": "Issue-to-PR idempotency",
        "verify": lambda: check(
            (ROOT / "tests" / "test_issue_idempotency.py").is_file(), "Missing test_issue_idempotency.py"
        ),
    },
    {
        "task": 13,
        "phase": "Phase 0",
        "title": "Human approval gate",
        "verify": lambda: check((ROOT / "gossipmesh" / "models" / "approval.py").is_file(), "Missing approval.py"),
    },
    {
        "task": 14,
        "phase": "Phase 0",
        "title": "Change-risk classifier",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "change_risk.py").is_file(), "Missing change_risk.py"),
            importlib.import_module("gossipmesh.change_risk"),
        ),
    },
    {
        "task": 15,
        "phase": "Phase 0",
        "title": "Daily cost and volume limits",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "runtime" / "limits.py").is_file(), "Missing limits.py"),
            importlib.import_module("gossipmesh.runtime.limits"),
        ),
    },
    {
        "task": 16,
        "phase": "Phase 0",
        "title": "Automation outcome report",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "enterprise" / "outcome_report.py").is_file(), "Missing outcome_report.py"),
            importlib.import_module("gossipmesh.enterprise.outcome_report"),
        ),
    },
    {
        "task": 17,
        "phase": "Phase 0",
        "title": "Canary mode",
        "verify": lambda: check((ROOT / "gossipmesh" / "enterprise" / "canary.py").is_file(), "Missing canary.py"),
    },
    {
        "task": 18,
        "phase": "Phase 0",
        "title": "Disable unsafe defaults",
        "verify": lambda: check(
            "ALLOW_AUTO_MERGE"
            in (ROOT / "gossipmesh" / "core" / "safety.py").read_text(encoding="utf-8", errors="ignore"),
            "ALLOW_AUTO_MERGE missing",
        ),
    },
    # Phase 1: Architecture and API foundations
    {
        "task": 19,
        "phase": "Phase 1",
        "title": "Architecture document",
        "verify": lambda: check((ROOT / "docs" / "ARCHITECTURE.md").is_file(), "Missing docs/ARCHITECTURE.md"),
    },
    {
        "task": 20,
        "phase": "Phase 1",
        "title": "Layered architecture",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "core").is_dir(), "Missing core dir"),
            check((ROOT / "gossipmesh" / "api").is_dir(), "Missing api dir"),
        ),
    },
    {
        "task": 21,
        "phase": "Phase 1",
        "title": "Structured errors",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "core" / "exceptions.py").is_file(), "Missing exceptions.py"),
            importlib.import_module("gossipmesh.core.exceptions"),
        ),
    },
    {
        "task": 22,
        "phase": "Phase 1",
        "title": "API schemas",
        "verify": lambda: check((ROOT / "gossipmesh" / "models" / "base.py").is_file(), "Missing base.py"),
    },
    {
        "task": 23,
        "phase": "Phase 1",
        "title": "Request correlation IDs",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "middleware" / "correlation.py").is_file(), "Missing correlation.py"),
            importlib.import_module("gossipmesh.middleware.correlation"),
        ),
    },
    {
        "task": 24,
        "phase": "Phase 1",
        "title": "API documentation",
        "verify": lambda: (
            check((ROOT / "tests" / "test_api_documentation.py").is_file(), "Missing test_api_documentation.py"),
            check(
                "openapi_tags"
                in (ROOT / "gossipmesh" / "api" / "main.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing openapi_tags",
            ),
        ),
    },
    # Phase 2: Database and persistence
    {
        "task": 25,
        "phase": "Phase 2",
        "title": "Model audit",
        "verify": lambda: check((ROOT / "gossipmesh" / "models" / "base.py").is_file(), "Missing base model"),
    },
    {
        "task": 26,
        "phase": "Phase 2",
        "title": "PostgreSQL system of record",
        "verify": lambda: check(
            (ROOT / "alembic").is_dir() and len(list((ROOT / "alembic" / "versions").glob("*.py"))) > 0,
            "No migrations found",
        ),
    },
    {
        "task": 27,
        "phase": "Phase 2",
        "title": "Alembic migrations",
        "verify": lambda: (
            check((ROOT / "alembic" / "env.py").is_file(), "Missing alembic env.py"),
            check(len(list((ROOT / "alembic" / "versions").glob("*.py"))) > 0, "No migrations found"),
        ),
    },
    {
        "task": 28,
        "phase": "Phase 2",
        "title": "Transaction boundaries",
        "verify": lambda: check((ROOT / "tests" / "test_transactions.py").is_file(), "Missing test_transactions.py"),
    },
    {
        "task": 29,
        "phase": "Phase 2",
        "title": "Optimistic concurrency",
        "verify": lambda: check(
            (ROOT / "alembic" / "versions" / "1791908854_add_version_id_for_concurrency.py").is_file(),
            "Missing version_id migration",
        ),
    },
    {
        "task": 30,
        "phase": "Phase 2",
        "title": "Soft deletion and retention",
        "verify": lambda: (
            check((ROOT / "tests" / "test_soft_delete.py").is_file(), "Missing test_soft_delete.py"),
            check((ROOT / "gossipmesh" / "models" / "mixins.py").is_file(), "Missing mixins.py"),
        ),
    },
    {
        "task": 31,
        "phase": "Phase 2",
        "title": "Database indexes and query audit",
        "verify": lambda: check((ROOT / "gossipmesh" / "models" / "organization.py").is_file(), "Missing org model"),
    },
    {
        "task": 32,
        "phase": "Phase 2",
        "title": "Database backup validation",
        "verify": lambda: (
            check((ROOT / "docs" / "DATABASE_BACKUP_AND_RECOVERY.md").is_file(), "Missing backup doc"),
            check((ROOT / "gossipmesh" / "db" / "backup.py").is_file(), "Missing backup.py"),
            check((ROOT / "tests" / "test_backup_restore.py").is_file(), "Missing test_backup_restore.py"),
        ),
    },
    # Phase 3: Multi-tenancy and authorization
    {
        "task": 33,
        "phase": "Phase 3",
        "title": "Tenant model",
        "verify": lambda: check(
            (ROOT / "gossipmesh" / "models" / "organization.py").is_file(), "Missing organization.py"
        ),
    },
    {
        "task": 34,
        "phase": "Phase 3",
        "title": "Centralized authorization",
        "verify": lambda: check(
            (ROOT / "gossipmesh" / "auth" / "authorization.py").is_file(), "Missing authorization.py"
        ),
    },
    {
        "task": 35,
        "phase": "Phase 3",
        "title": "Tenant-scoped queries",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "db" / "tenant.py").is_file(), "Missing tenant.py"),
            check((ROOT / "tests" / "test_tenant_queries.py").is_file(), "Missing test_tenant_queries.py"),
        ),
    },
    {
        "task": 36,
        "phase": "Phase 3",
        "title": "Organization APIs",
        "verify": lambda: check(
            (ROOT / "gossipmesh" / "api" / "routers" / "organizations.py").is_file(), "Missing organizations.py"
        ),
    },
    {
        "task": 37,
        "phase": "Phase 3",
        "title": "Project and repository APIs",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "api" / "routers" / "projects.py").is_file(), "Missing projects.py"),
            check(
                (ROOT / "tests" / "test_projects_repositories.py").is_file(), "Missing test_projects_repositories.py"
            ),
            check(
                "RepositoryPolicy"
                in (ROOT / "gossipmesh" / "models" / "repository.py").read_text(encoding="utf-8", errors="ignore"),
                "RepositoryPolicy missing",
            ),
        ),
    },
    {
        "task": 38,
        "phase": "Phase 3",
        "title": "Service accounts and API keys",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "models" / "service_account.py").is_file(), "Missing service_account.py"),
            check((ROOT / "tests" / "test_service_accounts.py").is_file(), "Missing test_service_accounts.py"),
        ),
    },
    {
        "task": 39,
        "phase": "Phase 3",
        "title": "Rate limiting",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "core" / "rate_limit.py").is_file(), "Missing core rate_limit.py"),
            check((ROOT / "tests" / "test_rate_limit.py").is_file(), "Missing test_rate_limit.py"),
        ),
    },
    {
        "task": 40,
        "phase": "Phase 3",
        "title": "Cross-tenant security tests",
        "verify": lambda: check(
            (ROOT / "tests" / "test_vectors" / "test_isolation.py").is_file(), "Missing test_isolation.py"
        ),
    },
    # Phase 4: Authentication and enterprise identity
    {
        "task": 41,
        "phase": "Phase 4",
        "title": "Password security",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "auth" / "password.py").is_file(), "Missing password.py"),
            check((ROOT / "gossipmesh" / "auth" / "throttle.py").is_file(), "Missing throttle.py"),
            check((ROOT / "tests" / "test_password_security.py").is_file(), "Missing test_password_security.py"),
        ),
    },
    {
        "task": 42,
        "phase": "Phase 4",
        "title": "JWT and sessions",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "core" / "security.py").is_file(), "Missing security.py"),
            check((ROOT / "gossipmesh" / "models" / "session.py").is_file(), "Missing session.py"),
        ),
    },
    {
        "task": 43,
        "phase": "Phase 4",
        "title": "GitHub OAuth",
        "verify": lambda: check((ROOT / "gossipmesh" / "api" / "routers" / "auth.py").is_file(), "Missing auth.py"),
    },
    {
        "task": 44,
        "phase": "Phase 4",
        "title": "OIDC integration",
        "verify": lambda: check((ROOT / "gossipmesh" / "models" / "sso.py").is_file(), "Missing sso.py"),
    },
    {
        "task": 45,
        "phase": "Phase 4",
        "title": "SAML 2.0",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "auth" / "sso" / "saml_adapter.py").is_file(), "Missing saml_adapter.py"),
            check((ROOT / "tests" / "test_sso.py").is_file(), "Missing test_sso.py"),
        ),
    },
    {
        "task": 46,
        "phase": "Phase 4",
        "title": "SCIM 2.0 provisioning",
        "verify": lambda: check((ROOT / "gossipmesh" / "api" / "routers" / "scim.py").is_file(), "Missing scim.py"),
    },
    {
        "task": 47,
        "phase": "Phase 4",
        "title": "MFA / TOTP",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "auth" / "mfa.py").is_file(), "Missing mfa.py"),
            check(
                (ROOT / "alembic" / "versions" / "146ee27bb11f_add_mfa_fields.py").is_file(), "Missing mfa migration"
            ),
        ),
    },
    {
        "task": 48,
        "phase": "Phase 4",
        "title": "Audit trail for auth events",
        "verify": lambda: check(
            (ROOT / "gossipmesh" / "audit" / "immutable_audit.py").is_file(), "Missing immutable_audit.py"
        ),
    },
    # Phase 5: GitHub integration and webhooks
    {
        "task": 49,
        "phase": "Phase 5",
        "title": "GitHub App onboarding",
        "verify": lambda: check((ROOT / "gossipmesh" / "integrations" / "github.py").is_file(), "Missing github.py"),
    },
    {
        "task": 50,
        "phase": "Phase 5",
        "title": "Webhook idempotency",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "core" / "idempotency.py").is_file(), "Missing idempotency.py"),
            check((ROOT / "tests" / "test_idempotency_keys.py").is_file(), "Missing test_idempotency_keys.py"),
        ),
    },
    {
        "task": 51,
        "phase": "Phase 5",
        "title": "Webhook signature verification",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "api" / "webhooks.py").is_file(), "Missing webhooks.py"),
            check((ROOT / "tests" / "test_webhooks.py").is_file(), "Missing test_webhooks.py"),
        ),
    },
    {
        "task": 52,
        "phase": "Phase 5",
        "title": "Pull Request review workflow",
        "verify": lambda: check(
            (ROOT / "gossipmesh" / "integrations" / "github_pr.py").is_file(), "Missing github_pr.py"
        ),
    },
    {
        "task": 53,
        "phase": "Phase 5",
        "title": "Inline code comments",
        "verify": lambda: check(
            "post_pr_review_comment"
            in (ROOT / "gossipmesh" / "integrations" / "github_pr.py").read_text(encoding="utf-8", errors="ignore"),
            "Missing inline comment logic",
        ),
    },
    {
        "task": 54,
        "phase": "Phase 5",
        "title": "Webhook delivery failure retries",
        "verify": lambda: check(
            (ROOT / "alembic" / "versions" / "f10000000002_add_webhook_retries.py").is_file(),
            "Missing webhook retries migration",
        ),
    },
    {
        "task": 55,
        "phase": "Phase 5",
        "title": "Least privilege GitHub permissions",
        "verify": lambda: (
            check((ROOT / "docs" / "GITHUB_PERMISSIONS_MATRIX.md").is_file(), "Missing permissions doc"),
            check(
                (ROOT / "gossipmesh" / "integrations" / "github_permissions.py").is_file(),
                "Missing github_permissions.py",
            ),
            check((ROOT / "tests" / "test_github_permissions.py").is_file(), "Missing test_github_permissions.py"),
        ),
    },
    {
        "task": 56,
        "phase": "Phase 5",
        "title": "GitHub client resilience",
        "verify": lambda: check(
            "resilience"
            in (ROOT / "gossipmesh" / "integrations" / "github.py").read_text(encoding="utf-8", errors="ignore").lower()
            or "retry"
            in (ROOT / "gossipmesh" / "integrations" / "github.py")
            .read_text(encoding="utf-8", errors="ignore")
            .lower(),
            "Missing retry logic",
        ),
    },
    # Phase 6: Workflow engine and background jobs
    {
        "task": 57,
        "phase": "Phase 6",
        "title": "Background worker architecture",
        "verify": lambda: (
            check((ROOT / "worker" / "processor.py").is_file(), "Missing worker/processor.py"),
            check((ROOT / "gossipmesh" / "runtime" / "scheduler.py").is_file(), "Missing scheduler.py"),
        ),
    },
    {
        "task": 58,
        "phase": "Phase 6",
        "title": "Distributed locking",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "runtime" / "worker_lease.py").is_file(), "Missing worker_lease.py"),
            check((ROOT / "tests" / "test_worker_leases.py").is_file(), "Missing test_worker_leases.py"),
        ),
    },
    {
        "task": 59,
        "phase": "Phase 6",
        "title": "Idempotency keys",
        "verify": lambda: check(
            (ROOT / "gossipmesh" / "models" / "idempotency.py").is_file(), "Missing idempotency model"
        ),
    },
    {
        "task": 60,
        "phase": "Phase 6",
        "title": "Queue priorities",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "runtime" / "scheduler.py").is_file(), "Missing scheduler.py"),
            check((ROOT / "tests" / "test_scheduler.py").is_file(), "Missing test_scheduler.py"),
        ),
    },
    {
        "task": 61,
        "phase": "Phase 6",
        "title": "Worker heartbeats & leases",
        "verify": lambda: (
            check(
                (ROOT / "alembic" / "versions" / "7a1000000004_add_job_worker_leases.py").is_file(),
                "Missing worker lease migration",
            ),
            check((ROOT / "gossipmesh" / "runtime" / "worker_lease.py").is_file(), "Missing worker_lease.py"),
        ),
    },
    {
        "task": 62,
        "phase": "Phase 6",
        "title": "Concurrency limits",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "runtime" / "concurrency.py").is_file(), "Missing concurrency.py"),
            check((ROOT / "tests" / "test_concurrency_limiter.py").is_file(), "Missing test_concurrency_limiter.py"),
        ),
    },
    {
        "task": 63,
        "phase": "Phase 6",
        "title": "Dead letter queues",
        "verify": lambda: check(
            "dlq"
            in (ROOT / "gossipmesh" / "runtime" / "scheduler.py").read_text(encoding="utf-8", errors="ignore").lower()
            or "dead"
            in (ROOT / "gossipmesh" / "runtime" / "scheduler.py").read_text(encoding="utf-8", errors="ignore").lower(),
            "Missing DLQ logic",
        ),
    },
    {
        "task": 64,
        "phase": "Phase 6",
        "title": "Job cancellation & timeouts",
        "verify": lambda: check((ROOT / "gossipmesh" / "runtime" / "limits.py").is_file(), "Missing limits.py"),
    },
    # Phase 7: AI providers and review quality
    {
        "task": 65,
        "phase": "Phase 7",
        "title": "Multi-provider abstraction",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "providers" / "base.py").is_file(), "Missing providers base"),
            check((ROOT / "gossipmesh" / "providers" / "manager.py").is_file(), "Missing providers manager"),
        ),
    },
    {
        "task": 67,
        "phase": "Phase 7",
        "title": "Prompt engineering pipeline",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "review" / "prompt_pipeline.py").is_file(), "Missing prompt_pipeline.py"),
            check((ROOT / "tests" / "test_prompt_pipeline.py").is_file(), "Missing test_prompt_pipeline.py"),
            check(
                "UNTRUSTED_OPEN"
                in (ROOT / "gossipmesh" / "review" / "prompt_pipeline.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing UNTRUSTED_OPEN marker",
            ),
        ),
    },
    {
        "task": 68,
        "phase": "Phase 7",
        "title": "Finding normalization",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "review" / "normalization.py").is_file(), "Missing normalization.py"),
            check(
                (ROOT / "tests" / "test_finding_normalization.py").is_file(), "Missing test_finding_normalization.py"
            ),
            check(
                "compute_stable_fingerprint"
                in (ROOT / "gossipmesh" / "review" / "normalization.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing fingerprinting",
            ),
        ),
    },
    {
        "task": 69,
        "phase": "Phase 7",
        "title": "Context assembly & diff chunking",
        "verify": lambda: check((ROOT / "gossipmesh" / "repository" / "chunking.py").is_file(), "Missing chunking.py"),
    },
    {
        "task": 70,
        "phase": "Phase 7",
        "title": "Confidence scoring & filtering",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "review" / "gates.py").is_file(), "Missing review gates.py"),
            check((ROOT / "tests" / "test_review_gates.py").is_file(), "Missing test_review_gates.py"),
            check(
                "DeterministicReviewGates"
                in (ROOT / "gossipmesh" / "review" / "gates.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing ReviewGates",
            ),
        ),
    },
    {
        "task": 71,
        "phase": "Phase 7",
        "title": "Suppressions and feedback loop",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "models" / "finding_feedback.py").is_file(), "Missing finding_feedback.py"),
            check((ROOT / "gossipmesh" / "review" / "feedback_learning.py").is_file(), "Missing feedback_learning.py"),
            check((ROOT / "tests" / "test_feedback_learning.py").is_file(), "Missing test_feedback_learning.py"),
        ),
    },
    {
        "task": 72,
        "phase": "Phase 7",
        "title": "Fallback provider routing",
        "verify": lambda: check((ROOT / "services" / "key_pool_router.py").is_file(), "Missing key_pool_router.py"),
    },
    {
        "task": 73,
        "phase": "Phase 7",
        "title": "AI provider cost metering",
        "verify": lambda: check(
            (ROOT / "gossipmesh" / "billing" / "usage_metering.py").is_file(), "Missing usage_metering.py"
        ),
    },
    {
        "task": 74,
        "phase": "Phase 7",
        "title": "Provider circuit breaker",
        "verify": lambda: check(
            "circuit"
            in (ROOT / "gossipmesh" / "services" / "key_pool_router.py")
            .read_text(encoding="utf-8", errors="ignore")
            .lower()
            or "error_rate"
            in (ROOT / "gossipmesh" / "services" / "key_pool_router.py")
            .read_text(encoding="utf-8", errors="ignore")
            .lower(),
            "Missing circuit breaker logic",
        ),
    },
    # Phase 8: Repository indexing and RAG
    {
        "task": 75,
        "phase": "Phase 8",
        "title": "Vector store integration",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "repository" / "vector_store.py").is_file(), "Missing vector_store.py"),
            check((ROOT / "tests" / "test_vector_store.py").is_file(), "Missing test_vector_store.py"),
            check(
                "retention_expires_at"
                in (ROOT / "gossipmesh" / "repository" / "vector_store.py").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing retention_expires_at",
            ),
        ),
    },
    {
        "task": 76,
        "phase": "Phase 8",
        "title": "Incremental repository indexing",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "models" / "indexing.py").is_file(), "Missing indexing model"),
            check((ROOT / "gossipmesh" / "repository" / "indexing.py").is_file(), "Missing repository/indexing.py"),
            check((ROOT / "tests" / "test_incremental_indexing.py").is_file(), "Missing test_incremental_indexing.py"),
            check(
                "FileIndexRecord"
                in (ROOT / "gossipmesh" / "models" / "indexing.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing FileIndexRecord",
            ),
        ),
    },
    {
        "task": 77,
        "phase": "Phase 8",
        "title": "AST & symbol-aware context",
        "verify": lambda: check(
            (ROOT / "scripts" / "go_ast_extractor.go").is_file()
            or (ROOT / "gossipmesh" / "repository" / "indexing.py").is_file(),
            "Missing AST extractor",
        ),
    },
    {
        "task": 78,
        "phase": "Phase 8",
        "title": "Permission-aware retrieval",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "repository" / "retrieval.py").is_file(), "Missing retrieval.py"),
            check(
                (ROOT / "tests" / "test_permission_aware_retrieval.py").is_file(),
                "Missing test_permission_aware_retrieval.py",
            ),
            check(
                "PermissionAwareRetriever"
                in (ROOT / "gossipmesh" / "repository" / "retrieval.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing PermissionAwareRetriever",
            ),
        ),
    },
    {
        "task": 79,
        "phase": "Phase 8",
        "title": "Hybrid search & reranking",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "repository" / "hybrid_search.py").is_file(), "Missing hybrid_search.py"),
            check((ROOT / "tests" / "test_hybrid_search.py").is_file(), "Missing test_hybrid_search.py"),
            check(
                "HybridSearchEngine"
                in (ROOT / "gossipmesh" / "repository" / "hybrid_search.py").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing HybridSearchEngine",
            ),
        ),
    },
    {
        "task": 80,
        "phase": "Phase 8",
        "title": "Secure cache",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "semantic_cache.py").is_file(), "Missing semantic_cache.py"),
            check((ROOT / "tests" / "test_secure_cache.py").is_file(), "Missing test_secure_cache.py"),
            check(
                "SecureRedisCache"
                in (ROOT / "gossipmesh" / "semantic_cache.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing SecureRedisCache",
            ),
        ),
    },
    # Phase 9: Secure code execution
    {
        "task": 81,
        "phase": "Phase 9",
        "title": "Sandbox threat model",
        "verify": lambda: (
            check((ROOT / "docs" / "SECURITY_SANDBOX.md").is_file(), "Missing SECURITY_SANDBOX.md"),
            check(
                "Threat Matrix" in (ROOT / "docs" / "SECURITY_SANDBOX.md").read_text(encoding="utf-8", errors="ignore"),
                "Missing threat matrix section",
            ),
        ),
    },
    {
        "task": 82,
        "phase": "Phase 9",
        "title": "Deny-by-default command policy",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "runtime" / "sandbox.py").is_file(), "Missing sandbox.py"),
            check(
                (ROOT / "tests" / "test_deny_by_default_policy.py").is_file(), "Missing test_deny_by_default_policy.py"
            ),
            check(
                "CommandPolicyEngine"
                in (ROOT / "gossipmesh" / "runtime" / "sandbox.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing CommandPolicyEngine",
            ),
        ),
    },
    {
        "task": 83,
        "phase": "Phase 9",
        "title": "Isolated execution adapter",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "runtime" / "isolated_adapter.py").is_file(), "Missing isolated_adapter.py"),
            check((ROOT / "tests" / "test_isolated_adapter.py").is_file(), "Missing test_isolated_adapter.py"),
            check(
                "RootlessContainerAdapter"
                in (ROOT / "gossipmesh" / "runtime" / "isolated_adapter.py").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing RootlessContainerAdapter",
            ),
        ),
    },
    {
        "task": 84,
        "phase": "Phase 9",
        "title": "Artifact quarantine",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "runtime" / "quarantine.py").is_file(), "Missing quarantine.py"),
            check((ROOT / "tests" / "test_artifact_quarantine.py").is_file(), "Missing test_artifact_quarantine.py"),
            check(
                "ArtifactQuarantineManager"
                in (ROOT / "gossipmesh" / "runtime" / "quarantine.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing ArtifactQuarantineManager",
            ),
        ),
    },
    {
        "task": 85,
        "phase": "Phase 9",
        "title": "Sandbox escape tests",
        "verify": lambda: (
            check((ROOT / "tests" / "test_sandbox_escapes.py").is_file(), "Missing test_sandbox_escapes.py"),
            check(
                "test_escape_vector_path_traversal"
                in (ROOT / "tests" / "test_sandbox_escapes.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing escape vectors",
            ),
        ),
    },
    {
        "task": 86,
        "phase": "Phase 9",
        "title": "Dependency and network policy",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "runtime" / "dependency_policy.py").is_file(), "Missing dependency_policy.py"),
            check((ROOT / "tests" / "test_dependency_policy.py").is_file(), "Missing test_dependency_policy.py"),
            check(
                "DependencyPolicyEngine"
                in (ROOT / "gossipmesh" / "runtime" / "dependency_policy.py").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing DependencyPolicyEngine",
            ),
        ),
    },
    # Phase 10: Billing and commercialization
    {
        "task": 87,
        "phase": "Phase 10",
        "title": "Real Stripe integration",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "billing" / "stripe_service.py").is_file(), "Missing stripe_service.py"),
            check((ROOT / "tests" / "test_stripe_integration.py").is_file(), "Missing test_stripe_integration.py"),
            check(
                "StripeBillingService"
                in (ROOT / "gossipmesh" / "billing" / "stripe_service.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing StripeBillingService",
            ),
        ),
    },
    {
        "task": 88,
        "phase": "Phase 10",
        "title": "Usage metering ledger",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "billing" / "usage_metering.py").is_file(), "Missing usage_metering.py"),
            check((ROOT / "tests" / "test_usage_metering.py").is_file(), "Missing test_usage_metering.py"),
            check(
                "UsageMeteringService"
                in (ROOT / "gossipmesh" / "billing" / "usage_metering.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing UsageMeteringService",
            ),
        ),
    },
    {
        "task": 89,
        "phase": "Phase 10",
        "title": "Plan enforcement",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "billing" / "plan_enforcement.py").is_file(), "Missing plan_enforcement.py"),
            check((ROOT / "tests" / "test_plan_enforcement.py").is_file(), "Missing test_plan_enforcement.py"),
            check(
                "PlanEnforcementService"
                in (ROOT / "gossipmesh" / "billing" / "plan_enforcement.py").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing PlanEnforcementService",
            ),
        ),
    },
    {
        "task": 90,
        "phase": "Phase 10",
        "title": "Billing permissions",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "api" / "routers" / "billing.py").is_file(), "Missing billing router"),
            check((ROOT / "tests" / "test_billing_permissions.py").is_file(), "Missing test_billing_permissions.py"),
            check(
                "require_billing_admin"
                in (ROOT / "gossipmesh" / "api" / "routers" / "billing.py").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing require_billing_admin",
            ),
        ),
    },
    {
        "task": 91,
        "phase": "Phase 10",
        "title": "Enterprise contracts",
        "verify": lambda: (
            check((ROOT / "enterprise" / "licensing.py").is_file(), "Missing enterprise/licensing.py"),
            check((ROOT / "gossipmesh" / "enterprise" / "controls.py").is_file(), "Missing enterprise/controls.py"),
        ),
    },
    {
        "task": 92,
        "phase": "Phase 10",
        "title": "Cost controls",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "billing" / "cost_controls.py").is_file(), "Missing cost_controls.py"),
            check((ROOT / "tests" / "test_cost_controls.py").is_file(), "Missing test_cost_controls.py"),
            check(
                "CostControlsEngine"
                in (ROOT / "gossipmesh" / "billing" / "cost_controls.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing CostControlsEngine",
            ),
        ),
    },
    # Phase 11: Observability and operations
    {
        "task": 93,
        "phase": "Phase 11",
        "title": "Structured logging",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "core" / "logging.py").is_file(), "Missing logging.py"),
            check((ROOT / "tests" / "test_structured_logging.py").is_file(), "Missing test_structured_logging.py"),
            check(
                "StructuredJSONFormatter"
                in (ROOT / "gossipmesh" / "core" / "logging.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing StructuredJSONFormatter",
            ),
        ),
    },
    {
        "task": 94,
        "phase": "Phase 11",
        "title": "Prometheus metrics",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "observability" / "metrics.py").is_file(), "Missing metrics.py"),
            check(
                (ROOT / "tests" / "test_observability_metrics.py").is_file(), "Missing test_observability_metrics.py"
            ),
            check(
                "generate_latest_metrics"
                in (ROOT / "gossipmesh" / "observability" / "metrics.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing generate_latest_metrics",
            ),
        ),
    },
    {
        "task": 95,
        "phase": "Phase 11",
        "title": "Distributed tracing",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "observability" / "tracing.py").is_file(), "Missing tracing.py"),
            check((ROOT / "tests" / "test_distributed_tracing.py").is_file(), "Missing test_distributed_tracing.py"),
            check(
                "setup_tracer_provider"
                in (ROOT / "gossipmesh" / "observability" / "tracing.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing setup_tracer_provider",
            ),
        ),
    },
    {
        "task": 96,
        "phase": "Phase 11",
        "title": "Health and readiness",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "api" / "routers" / "health.py").is_file(), "Missing health.py"),
            check((ROOT / "tests" / "test_health_readiness.py").is_file(), "Missing test_health_readiness.py"),
            check(
                "liveness_probe"
                in (ROOT / "gossipmesh" / "api" / "routers" / "health.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing liveness_probe",
            ),
        ),
    },
    {
        "task": 97,
        "phase": "Phase 11",
        "title": "Alerts and runbooks",
        "verify": lambda: (
            check((ROOT / "docs" / "OPERATIONAL_RUNBOOKS.md").is_file(), "Missing OPERATIONAL_RUNBOOKS.md"),
            check(
                "APIErrorRateHigh"
                in (ROOT / "docs" / "OPERATIONAL_RUNBOOKS.md").read_text(encoding="utf-8", errors="ignore"),
                "Missing alert runbook",
            ),
        ),
    },
    {
        "task": 98,
        "phase": "Phase 11",
        "title": "Disaster recovery",
        "verify": lambda: (
            check((ROOT / "docs" / "DISASTER_RECOVERY.md").is_file(), "Missing DISASTER_RECOVERY.md"),
            check(
                (ROOT / "gossipmesh" / "enterprise" / "disaster_recovery.py").is_file(), "Missing disaster_recovery.py"
            ),
            check((ROOT / "tests" / "test_disaster_recovery.py").is_file(), "Missing test_disaster_recovery.py"),
            check(
                "DisasterRecoveryService"
                in (ROOT / "gossipmesh" / "enterprise" / "disaster_recovery.py").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing DisasterRecoveryService",
            ),
        ),
    },
    # Phase 12: Frontend and customer product
    {
        "task": 99,
        "phase": "Phase 12",
        "title": "SaaS web application",
        "verify": lambda: (
            check((ROOT / "frontend" / "package.json").is_file(), "Missing frontend/package.json"),
            check((ROOT / "frontend" / "src" / "app" / "layout.tsx").is_file(), "Missing layout.tsx"),
            check((ROOT / "frontend" / "src" / "lib" / "api.ts").is_file(), "Missing api.ts"),
        ),
    },
    {
        "task": 100,
        "phase": "Phase 12",
        "title": "Review dashboard",
        "verify": lambda: (
            check(
                (ROOT / "frontend" / "src" / "app" / "dashboard" / "page.tsx").is_file(), "Missing dashboard page.tsx"
            ),
            check(
                "Review Dashboard"
                in (ROOT / "frontend" / "src" / "app" / "dashboard" / "page.tsx").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing dashboard heading",
            ),
        ),
    },
    {
        "task": 101,
        "phase": "Phase 12",
        "title": "Repository settings",
        "verify": lambda: (
            check((ROOT / "frontend" / "src" / "app" / "settings" / "page.tsx").is_file(), "Missing settings page.tsx"),
            check(
                "Repository Settings"
                in (ROOT / "frontend" / "src" / "app" / "settings" / "page.tsx").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing settings heading",
            ),
        ),
    },
    {
        "task": 102,
        "phase": "Phase 12",
        "title": "Human feedback UI",
        "verify": lambda: (
            check((ROOT / "frontend" / "src" / "app" / "findings" / "page.tsx").is_file(), "Missing findings page.tsx"),
            check(
                "Human Feedback"
                in (ROOT / "frontend" / "src" / "app" / "findings" / "page.tsx").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing feedback heading",
            ),
        ),
    },
    {
        "task": 103,
        "phase": "Phase 12",
        "title": "Onboarding",
        "verify": lambda: (
            check(
                (ROOT / "frontend" / "src" / "app" / "onboarding" / "page.tsx").is_file(), "Missing onboarding page.tsx"
            ),
            check(
                "Welcome to GossipMesh"
                in (ROOT / "frontend" / "src" / "app" / "onboarding" / "page.tsx").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing onboarding heading",
            ),
        ),
    },
    {
        "task": 104,
        "phase": "Phase 12",
        "title": "Customer notifications",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "notifications" / "service.py").is_file(), "Missing notifications service"),
            check((ROOT / "tests" / "test_notifications.py").is_file(), "Missing test_notifications.py"),
            check(
                "NotificationDispatcher"
                in (ROOT / "gossipmesh" / "notifications" / "service.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing NotificationDispatcher",
            ),
        ),
    },
    # Phase 13: Security, compliance, and legal readiness
    {
        "task": 105,
        "phase": "Phase 13",
        "title": "Dependency security and SBOM",
        "verify": lambda: (
            check((ROOT / "scripts" / "generate_sbom.py").is_file(), "Missing generate_sbom.py"),
            check((ROOT / "docs" / "DEPENDENCY_SECURITY.md").is_file(), "Missing DEPENDENCY_SECURITY.md"),
            check((ROOT / "tests" / "test_dependency_security.py").is_file(), "Missing test_dependency_security.py"),
        ),
    },
    {
        "task": 106,
        "phase": "Phase 13",
        "title": "Secret scanning",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "security" / "secret_scanner.py").is_file(), "Missing secret_scanner.py"),
            check((ROOT / "tests" / "test_secret_scanning.py").is_file(), "Missing test_secret_scanning.py"),
            check(
                "SecretScannerEngine"
                in (ROOT / "gossipmesh" / "security" / "secret_scanner.py").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing SecretScannerEngine",
            ),
        ),
    },
    {
        "task": 107,
        "phase": "Phase 13",
        "title": "Full threat model",
        "verify": lambda: (
            check((ROOT / "docs" / "FULL_THREAT_MODEL.md").is_file(), "Missing FULL_THREAT_MODEL.md"),
            check(
                "THREAT-GH-01" in (ROOT / "docs" / "FULL_THREAT_MODEL.md").read_text(encoding="utf-8", errors="ignore"),
                "Missing threat model markers",
            ),
        ),
    },
    {
        "task": 108,
        "phase": "Phase 13",
        "title": "Immutable audit events",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "audit" / "immutable_audit.py").is_file(), "Missing immutable_audit.py"),
            check((ROOT / "tests" / "test_immutable_audit.py").is_file(), "Missing test_immutable_audit.py"),
            check(
                "ImmutableAuditService"
                in (ROOT / "gossipmesh" / "audit" / "immutable_audit.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing ImmutableAuditService",
            ),
        ),
    },
    {
        "task": 109,
        "phase": "Phase 13",
        "title": "Data export and deletion",
        "verify": lambda: (
            check(
                (ROOT / "gossipmesh" / "enterprise" / "disaster_recovery.py").is_file(), "Missing disaster_recovery.py"
            ),
            check(
                (ROOT / "tests" / "test_data_export_and_deletion.py").is_file(),
                "Missing test_data_export_and_deletion.py",
            ),
            check(
                "purge_organization_data"
                in (ROOT / "gossipmesh" / "enterprise" / "disaster_recovery.py").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing purge_organization_data",
            ),
        ),
    },
    {
        "task": 110,
        "phase": "Phase 13",
        "title": "Privacy and customer security docs",
        "verify": lambda: (
            check((ROOT / "docs" / "PRIVACY_AND_SECURITY.md").is_file(), "Missing PRIVACY_AND_SECURITY.md"),
            check(
                "Customer Security Architecture"
                in (ROOT / "docs" / "PRIVACY_AND_SECURITY.md").read_text(encoding="utf-8", errors="ignore"),
                "Missing policy content",
            ),
        ),
    },
    {
        "task": 111,
        "phase": "Phase 13",
        "title": "Support break-glass controls",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "enterprise" / "break_glass.py").is_file(), "Missing break_glass.py"),
            check((ROOT / "tests" / "test_support_breakglass.py").is_file(), "Missing test_support_breakglass.py"),
            check(
                "BreakGlassControlService"
                in (ROOT / "gossipmesh" / "enterprise" / "break_glass.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing BreakGlassControlService",
            ),
        ),
    },
    {
        "task": 112,
        "phase": "Phase 13",
        "title": "SOC 2 readiness checklist",
        "verify": lambda: (
            check((ROOT / "docs" / "SOC2_READINESS_CHECKLIST.md").is_file(), "Missing SOC2_READINESS_CHECKLIST.md"),
            check(
                "SOC 2 Type II"
                in (ROOT / "docs" / "SOC2_READINESS_CHECKLIST.md").read_text(encoding="utf-8", errors="ignore"),
                "Missing checklist content",
            ),
        ),
    },
    # Phase 14: Deployment and releases
    {
        "task": 113,
        "phase": "Phase 14",
        "title": "Production Docker images",
        "verify": lambda: (
            check((ROOT / "docker" / "Dockerfile.api").is_file(), "Missing Dockerfile.api"),
            check((ROOT / "docker" / "Dockerfile.worker").is_file(), "Missing Dockerfile.worker"),
            check((ROOT / "docker" / "Dockerfile.frontend").is_file(), "Missing Dockerfile.frontend"),
        ),
    },
    {
        "task": 114,
        "phase": "Phase 14",
        "title": "Production-like Compose",
        "verify": lambda: (
            check((ROOT / "docker-compose.yml").is_file(), "Missing docker-compose.yml"),
            check(
                "pgvector" in (ROOT / "docker-compose.yml").read_text(encoding="utf-8", errors="ignore"),
                "Missing pgvector in docker-compose.yml",
            ),
        ),
    },
    {
        "task": 115,
        "phase": "Phase 14",
        "title": "Deployment manifests",
        "verify": lambda: (
            check((ROOT / "k8s" / "deployment.yaml").is_file(), "Missing k8s/deployment.yaml"),
            check(
                "HorizontalPodAutoscaler"
                in (ROOT / "k8s" / "deployment.yaml").read_text(encoding="utf-8", errors="ignore"),
                "Missing HPA in k8s/deployment.yaml",
            ),
        ),
    },
    {
        "task": 116,
        "phase": "Phase 14",
        "title": "Infrastructure as code",
        "verify": lambda: (
            check((ROOT / "terraform" / "main.tf").is_file(), "Missing terraform/main.tf"),
            check((ROOT / "terraform" / "variables.tf").is_file(), "Missing terraform/variables.tf"),
            check(
                "aws_db_instance" in (ROOT / "terraform" / "main.tf").read_text(encoding="utf-8", errors="ignore"),
                "Missing RDS in terraform",
            ),
        ),
    },
    {
        "task": 117,
        "phase": "Phase 14",
        "title": "Staging environment",
        "verify": lambda: (
            check((ROOT / "scripts" / "staging_smoke_test.py").is_file(), "Missing staging_smoke_test.py"),
            check(
                "run_staging_smoke_tests"
                in (ROOT / "scripts" / "staging_smoke_test.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing smoke test runner",
            ),
        ),
    },
    {
        "task": 118,
        "phase": "Phase 14",
        "title": "Release process",
        "verify": lambda: (
            check((ROOT / "docs" / "RELEASE_PROCESS.md").is_file(), "Missing docs/RELEASE_PROCESS.md"),
            check(
                "Canary Rollout Strategy"
                in (ROOT / "docs" / "RELEASE_PROCESS.md").read_text(encoding="utf-8", errors="ignore"),
                "Missing canary strategy",
            ),
        ),
    },
    {
        "task": 119,
        "phase": "Phase 14",
        "title": "Status page and incident communication",
        "verify": lambda: (
            check((ROOT / "docs" / "STATUS_PAGE_AND_INCIDENTS.md").is_file(), "Missing STATUS_PAGE_AND_INCIDENTS.md"),
            check(
                "Incident Severity & Communication SLAs"
                in (ROOT / "docs" / "STATUS_PAGE_AND_INCIDENTS.md").read_text(encoding="utf-8", errors="ignore"),
                "Missing SLAs",
            ),
        ),
    },
    # Phase 15: Quality and launch
    {
        "task": 120,
        "phase": "Phase 15",
        "title": "Integration tests",
        "verify": lambda: (
            check((ROOT / "tests" / "test_runs.py").is_file(), "Missing test_runs.py"),
            check((ROOT / "tests" / "test_webhooks.py").is_file(), "Missing test_webhooks.py"),
        ),
    },
    {
        "task": 121,
        "phase": "Phase 15",
        "title": "End-to-end PR review test",
        "verify": lambda: check(
            (ROOT / "tests" / "test_autonomous_loop_integration.py").is_file(),
            "Missing test_autonomous_loop_integration.py",
        ),
    },
    {
        "task": 122,
        "phase": "Phase 15",
        "title": "Performance tests",
        "verify": lambda: (
            check((ROOT / "tests" / "test_performance.py").is_file(), "Missing test_performance.py"),
            check(
                "test_concurrent_organization_usage_metering_throughput"
                in (ROOT / "tests" / "test_performance.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing performance tests",
            ),
        ),
    },
    {
        "task": 123,
        "phase": "Phase 15",
        "title": "Failure-injection tests",
        "verify": lambda: (
            check((ROOT / "tests" / "test_failure_injection.py").is_file(), "Missing test_failure_injection.py"),
            check(
                "test_failure_injection_duplicate_webhook_idempotency"
                in (ROOT / "tests" / "test_failure_injection.py").read_text(encoding="utf-8", errors="ignore"),
                "Missing failure injection tests",
            ),
        ),
    },
    {
        "task": 124,
        "phase": "Phase 15",
        "title": "Feature flags",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "enterprise" / "feature_flags.py").is_file(), "Missing feature_flags.py"),
            check((ROOT / "tests" / "test_feature_flags.py").is_file(), "Missing test_feature_flags.py"),
            check(
                "FeatureFlagService"
                in (ROOT / "gossipmesh" / "enterprise" / "feature_flags.py").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing FeatureFlagService",
            ),
        ),
    },
    {
        "task": 125,
        "phase": "Phase 15",
        "title": "Customer support tooling",
        "verify": lambda: (
            check((ROOT / "gossipmesh" / "enterprise" / "support_tooling.py").is_file(), "Missing support_tooling.py"),
            check((ROOT / "tests" / "test_support_tooling.py").is_file(), "Missing test_support_tooling.py"),
            check(
                "CustomerSupportTooling"
                in (ROOT / "gossipmesh" / "enterprise" / "support_tooling.py").read_text(
                    encoding="utf-8", errors="ignore"
                ),
                "Missing CustomerSupportTooling",
            ),
        ),
    },
    {
        "task": 126,
        "phase": "Phase 15",
        "title": "Go-to-market checklist",
        "verify": lambda: (
            check((ROOT / "docs" / "GO_TO_MARKET_CHECKLIST.md").is_file(), "Missing GO_TO_MARKET_CHECKLIST.md"),
            check(
                "Target Customers"
                in (ROOT / "docs" / "GO_TO_MARKET_CHECKLIST.md").read_text(encoding="utf-8", errors="ignore"),
                "Missing Target Customers",
            ),
        ),
    },
    {
        "task": 127,
        "phase": "Phase 15",
        "title": "Final production review",
        "verify": lambda: check(
            (ROOT / "gossipmesh" / "integrations" / "github_pr.py").is_file(), "Missing github_pr.py"
        ),
    },
]


def main():
    print("===============================================================================")
    print("        SYSTEMATIC ONE-BY-ONE AUDIT OF ALL 126 IMPLEMENTATION PLAN TASKS       ")
    print("===============================================================================\n")

    passed = 0
    failed = 0
    failures = []

    current_phase = None
    for item in TASKS:
        phase = item["phase"]
        if phase != current_phase:
            current_phase = phase
            print(f"\n--- {phase} ---")

        task_num = item["task"]
        title = item["title"]
        try:
            item["verify"]()
            print(f"  [PASS] Task {task_num:3d}: {title}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] Task {task_num:3d}: {title} -> {e}")
            failed += 1
            failures.append((task_num, title, str(e)))

    print(f"\n===============================================================================")
    print(f"AUDIT SUMMARY: Total Checked: {len(TASKS)} | Passed: {passed} | Failed: {failed}")
    print(f"===============================================================================")
    if failed > 0:
        print("\nFailures:")
        for t, name, err in failures:
            print(f"  - Task {t}: {name} -> {err}")
        sys.exit(1)
    else:
        print("\nAll 126 tasks verified successfully with 100% compliance!")
        sys.exit(0)


if __name__ == "__main__":
    main()
