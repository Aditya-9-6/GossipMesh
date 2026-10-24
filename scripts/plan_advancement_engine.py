#!/usr/bin/env python3
"""
GossipMesh Enterprise SaaS Plan Advancement Engine.
Parses docs/ENTERPRISE_SAAS_IMPLEMENTATION_PLAN.md, audits the codebase to determine
which tasks are already completed, finds the next pending task, and creates issues
ready for autonomous solving and PR creation.
"""

import os
import sys
import re
import json
import subprocess
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PLAN_FILE = Path("docs/ENTERPRISE_SAAS_IMPLEMENTATION_PLAN.md")


class PlanTask:
    def __init__(self, num: int, name: str, phase: str, header: str, spec: str):
        self.num = num
        self.name = name
        self.phase = phase
        self.header = header
        self.spec = spec
        self.status = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED
        self.evidence: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num": self.num,
            "name": self.name,
            "phase": self.phase,
            "status": self.status,
            "evidence": self.evidence,
        }


def parse_implementation_plan(workspace: Path) -> List[PlanTask]:
    """Extracts all tasks defined in docs/ENTERPRISE_SAAS_IMPLEMENTATION_PLAN.md."""
    plan_path = workspace / PLAN_FILE
    if not plan_path.is_file():
        raise FileNotFoundError(f"Plan file not found: {plan_path}")

    content = plan_path.read_text(encoding="utf-8")
    phases = re.split(r"\n# (Phase \d+ [^\n]+)", content)
    tasks = []

    for i in range(1, len(phases), 2):
        p_name = phases[i].strip()
        p_body = phases[i + 1]
        raw_tasks = re.split(r"\n## (Task \d+ [^\n]+)", p_body)
        for j in range(1, len(raw_tasks), 2):
            t_header = raw_tasks[j].strip()
            t_spec = raw_tasks[j + 1].strip()
            # Remove trailing summary headers if parsed into last task
            if "\n---" in t_spec:
                t_spec = t_spec.split("\n---")[0].strip()

            m = re.match(r"Task (\d+)\s*[—–-]\s*(.+)", t_header)
            if m:
                t_num = int(m.group(1))
                t_name = m.group(2).strip()
                tasks.append(PlanTask(num=t_num, name=t_name, phase=p_name, header=t_header, spec=t_spec))

    return tasks


def audit_codebase_completion(tasks: List[PlanTask], workspace: Path):
    """
    Inspects git commit history, PRs, and workspace files to identify completed tasks.
    """
    # 1. Fetch merged and open PRs
    merged_prs = {}
    open_prs = {}
    try:
        cmd = [
            "gh",
            "pr",
            "list",
            "--repo",
            "Aditya-9-6/GossipMesh",
            "--state",
            "all",
            "--limit",
            "200",
            "--json",
            "number,title,state,headRefName",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=workspace)
        if res.returncode == 0 and res.stdout.strip():
            all_prs = json.loads(res.stdout)
            for pr in all_prs:
                num = pr.get("number")
                title = pr.get("title", "")
                state = pr.get("state", "")
                head = pr.get("headRefName", "")
                if state == "MERGED":
                    merged_prs[num] = (title, head)
                elif state == "OPEN":
                    open_prs[num] = (title, head)
    except Exception as e:
        print(f"[WARN] Failed to fetch PRs: {e}", file=sys.stderr)

    # 2. Fetch open issues
    open_issues = {}
    try:
        cmd = [
            "gh",
            "issue",
            "list",
            "--repo",
            "Aditya-9-6/GossipMesh",
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,title",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=workspace)
        if res.returncode == 0 and res.stdout.strip():
            issues = json.loads(res.stdout)
            for iss in issues:
                open_issues[iss["number"]] = iss.get("title", "")
    except Exception as e:
        print(f"[WARN] Failed to fetch issues: {e}", file=sys.stderr)

    # Specific file-based and semantic verifications
    CODEBASE_CHECKS = {
        1: lambda: (
            (workspace / "docs" / "PRODUCTION_READINESS.md").is_file()
            and "Audit" in (workspace / "docs" / "PRODUCTION_READINESS.md").read_text(encoding="utf-8", errors="ignore")
        ),
        2: lambda: (
            (workspace / "README.md").is_file()
            and "prototype" in (workspace / "README.md").read_text(encoding="utf-8", errors="ignore").lower()
        ),
        3: lambda: (workspace / "CONTRIBUTING.md").is_file() and (workspace / "SECURITY.md").is_file(),
        4: lambda: (
            "pytest" in (workspace / "pyproject.toml").read_text(encoding="utf-8", errors="ignore")
            if (workspace / "pyproject.toml").is_file()
            else False
        ),
        5: lambda: (
            "[tool.ruff]" in (workspace / "pyproject.toml").read_text(encoding="utf-8", errors="ignore")
            if (workspace / "pyproject.toml").is_file()
            else False
        ),
        6: lambda: (workspace / ".github" / "workflows" / "ci.yml").is_file(),
        7: lambda: any("terminology" in title.lower() for title, _ in merged_prs.values()),
        8: lambda: (
            "GOSSIPMESH_AUTOMATION_ENABLED"
            in (workspace / "scripts" / "autonomous_loop.py").read_text(encoding="utf-8", errors="ignore")
            if (workspace / "scripts" / "autonomous_loop.py").is_file()
            else False
        ),
        19: lambda: (workspace / "docs" / "ARCHITECTURE.md").is_file(),
        20: lambda: (workspace / "gossipmesh" / "enterprise").is_dir() and (workspace / "gossipmesh" / "core").is_dir(),
        23: lambda: (workspace / "gossipmesh" / "core" / "exceptions.py").is_file(),
        25: lambda: (workspace / "gossipmesh" / "middleware" / "correlation.py").is_file(),
        26: lambda: (
            (workspace / "alembic").is_dir() and len(list((workspace / "alembic" / "versions").glob("*.py"))) > 0
        ),
        28: lambda: any("transaction boundaries" in title.lower() for title, _ in merged_prs.values()),
        29: lambda: any("optimistic concurrency" in title.lower() for title, _ in merged_prs.values()),
        30: lambda: any(
            "soft delete" in title.lower() or "safe deletion" in title.lower() for title, _ in merged_prs.values()
        ),
        33: lambda: (workspace / "gossipmesh" / "models" / "organization.py").is_file(),
        34: lambda: (
            (workspace / "gossipmesh" / "auth" / "authorization.py").is_file()
            or any("centralized authorization" in title.lower() for title, _ in merged_prs.values())
        ),
        35: lambda: (
            (workspace / "gossipmesh" / "db" / "tenant.py").is_file()
            and (workspace / "tests" / "test_tenant_queries.py").is_file()
        ),
        36: lambda: (workspace / "gossipmesh" / "api" / "routers" / "organizations.py").is_file(),
        37: lambda: (
            (workspace / "gossipmesh" / "api" / "routers" / "projects.py").is_file()
            and (workspace / "tests" / "test_projects_repositories.py").is_file()
            and "RepositoryPolicy"
            in (workspace / "gossipmesh" / "models" / "repository.py").read_text(encoding="utf-8", errors="ignore")
        ),
        38: lambda: (
            (workspace / "gossipmesh" / "models" / "service_account.py").is_file()
            or any("service account" in title.lower() for title, _ in merged_prs.values())
        ),
        39: lambda: (workspace / "gossipmesh" / "core" / "rate_limit.py").is_file(),
        40: lambda: any(
            "cross-tenant" in title.lower() or "isolation" in title.lower() for title, _ in merged_prs.values()
        ),
        41: lambda: any(
            "password" in title.lower() and "security" in title.lower() for title, _ in merged_prs.values()
        ),
        42: lambda: any("jwt" in title.lower() and "session" in title.lower() for title, _ in merged_prs.values()),
        43: lambda: any("github oauth" in title.lower() for title, _ in merged_prs.values()),
        44: lambda: any("oidc" in title.lower() for title, _ in merged_prs.values()),
        45: lambda: (
            (workspace / "gossipmesh" / "models" / "saml.py").is_file()
            or any("saml" in title.lower() for title, _ in merged_prs.values())
        ),
        46: lambda: (
            (workspace / "gossipmesh" / "api" / "routers" / "scim.py").is_file()
            or any("scim" in title.lower() for title, _ in merged_prs.values())
        ),
        47: lambda: (
            (workspace / "gossipmesh" / "auth" / "mfa.py").is_file()
            or any("mfa" in title.lower() for title, _ in merged_prs.values())
        ),
        49: lambda: any(
            "webhook" in title.lower() and "idempotency" in title.lower() for title, _ in merged_prs.values()
        ),
        50: lambda: (
            (workspace / "gossipmesh" / "integrations" / "github_app.py").is_file()
            or any("github app" in title.lower() for title, _ in merged_prs.values())
        ),
        51: lambda: (workspace / "gossipmesh" / "api" / "routers" / "repositories.py").is_file(),
        52: lambda: (workspace / "gossipmesh" / "integrations" / "github_pr.py").is_file(),
        53: lambda: any("inline review" in title.lower() for title, _ in merged_prs.values()),
        54: lambda: any("webhook replay" in title.lower() for title, _ in merged_prs.values()),
        56: lambda: (
            (workspace / "gossipmesh" / "integrations" / "github_client.py").is_file()
            or any("github integration failure" in title.lower() for title, _ in merged_prs.values())
        ),
        57: lambda: (
            (workspace / "gossipmesh" / "worker" / "celery_app.py").is_file()
            or (workspace / "gossipmesh" / "models" / "jobs.py").is_file()
        ),
        59: lambda: (
            (workspace / "gossipmesh" / "core" / "idempotency.py").is_file()
            and (workspace / "tests" / "test_idempotency_keys.py").is_file()
            and (workspace / "gossipmesh" / "models" / "idempotency.py").is_file()
        ),
        61: lambda: (
            (workspace / "gossipmesh" / "runtime" / "concurrency.py").is_file()
            and (workspace / "tests" / "test_concurrency_limiter.py").is_file()
        ),
        63: lambda: (
            (workspace / "gossipmesh" / "runtime" / "worker_lease.py").is_file()
            and (workspace / "tests" / "test_worker_leases.py").is_file()
        ),
        64: lambda: (
            (workspace / "gossipmesh" / "runtime" / "scheduler.py").is_file()
            and (workspace / "tests" / "test_scheduler.py").is_file()
        ),
        70: lambda: (
            (workspace / "gossipmesh" / "review" / "prompt_pipeline.py").is_file()
            and (workspace / "tests" / "test_prompt_pipeline.py").is_file()
            and "UNTRUSTED_OPEN"
            in (workspace / "gossipmesh" / "review" / "prompt_pipeline.py").read_text(encoding="utf-8", errors="ignore")
        ),
        71: lambda: (
            (workspace / "gossipmesh" / "review" / "normalization.py").is_file()
            and (workspace / "tests" / "test_finding_normalization.py").is_file()
            and "compute_stable_fingerprint"
            in (workspace / "gossipmesh" / "review" / "normalization.py").read_text(encoding="utf-8", errors="ignore")
        ),
        72: lambda: (
            (workspace / "gossipmesh" / "review" / "gates.py").is_file()
            and (workspace / "tests" / "test_review_gates.py").is_file()
            and "DeterministicReviewGates"
            in (workspace / "gossipmesh" / "review" / "gates.py").read_text(encoding="utf-8", errors="ignore")
        ),
        74: lambda: (
            (workspace / "gossipmesh" / "models" / "finding_feedback.py").is_file()
            and (workspace / "gossipmesh" / "review" / "feedback_learning.py").is_file()
            and (workspace / "tests" / "test_feedback_learning.py").is_file()
        ),
        75: lambda: (
            (workspace / "gossipmesh" / "repository" / "vector_store.py").is_file()
            and (workspace / "tests" / "test_vector_store.py").is_file()
            and "retention_expires_at"
            in (workspace / "gossipmesh" / "repository" / "vector_store.py").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        76: lambda: (
            (workspace / "gossipmesh" / "models" / "indexing.py").is_file()
            and (workspace / "gossipmesh" / "repository" / "indexing.py").is_file()
            and (workspace / "tests" / "test_incremental_indexing.py").is_file()
            and "FileIndexRecord"
            in (workspace / "gossipmesh" / "models" / "indexing.py").read_text(encoding="utf-8", errors="ignore")
        ),
        78: lambda: (
            (workspace / "gossipmesh" / "repository" / "retrieval.py").is_file()
            and (workspace / "tests" / "test_permission_aware_retrieval.py").is_file()
            and "PermissionAwareRetriever"
            in (workspace / "gossipmesh" / "repository" / "retrieval.py").read_text(encoding="utf-8", errors="ignore")
        ),
        79: lambda: (
            (workspace / "gossipmesh" / "repository" / "hybrid_search.py").is_file()
            and (workspace / "tests" / "test_hybrid_search.py").is_file()
            and "HybridSearchEngine"
            in (workspace / "gossipmesh" / "repository" / "hybrid_search.py").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        80: lambda: (
            (workspace / "gossipmesh" / "semantic_cache.py").is_file()
            and (workspace / "tests" / "test_secure_cache.py").is_file()
            and "SecureRedisCache"
            in (workspace / "gossipmesh" / "semantic_cache.py").read_text(encoding="utf-8", errors="ignore")
        ),
        81: lambda: (
            (workspace / "docs" / "SECURITY_SANDBOX.md").is_file()
            and "Threat Matrix"
            in (workspace / "docs" / "SECURITY_SANDBOX.md").read_text(encoding="utf-8", errors="ignore")
        ),
        82: lambda: (
            (workspace / "gossipmesh" / "runtime" / "sandbox.py").is_file()
            and (workspace / "tests" / "test_deny_by_default_policy.py").is_file()
            and "CommandPolicyEngine"
            in (workspace / "gossipmesh" / "runtime" / "sandbox.py").read_text(encoding="utf-8", errors="ignore")
        ),
        83: lambda: (
            (workspace / "gossipmesh" / "runtime" / "isolated_adapter.py").is_file()
            and (workspace / "tests" / "test_isolated_adapter.py").is_file()
            and "RootlessContainerAdapter"
            in (workspace / "gossipmesh" / "runtime" / "isolated_adapter.py").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        84: lambda: (
            (workspace / "gossipmesh" / "runtime" / "quarantine.py").is_file()
            and (workspace / "tests" / "test_artifact_quarantine.py").is_file()
            and "ArtifactQuarantineManager"
            in (workspace / "gossipmesh" / "runtime" / "quarantine.py").read_text(encoding="utf-8", errors="ignore")
        ),
        85: lambda: (
            (workspace / "tests" / "test_sandbox_escapes.py").is_file()
            and "test_escape_vector_path_traversal"
            in (workspace / "tests" / "test_sandbox_escapes.py").read_text(encoding="utf-8", errors="ignore")
        ),
        86: lambda: (
            (workspace / "gossipmesh" / "runtime" / "dependency_policy.py").is_file()
            and (workspace / "tests" / "test_dependency_policy.py").is_file()
            and "DependencyPolicyEngine"
            in (workspace / "gossipmesh" / "runtime" / "dependency_policy.py").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        87: lambda: (
            (workspace / "gossipmesh" / "billing" / "stripe_service.py").is_file()
            and (workspace / "tests" / "test_stripe_integration.py").is_file()
            and "StripeBillingService"
            in (workspace / "gossipmesh" / "billing" / "stripe_service.py").read_text(encoding="utf-8", errors="ignore")
        ),
        88: lambda: (
            (workspace / "gossipmesh" / "billing" / "usage_metering.py").is_file()
            and (workspace / "tests" / "test_usage_metering.py").is_file()
            and "UsageMeteringService"
            in (workspace / "gossipmesh" / "billing" / "usage_metering.py").read_text(encoding="utf-8", errors="ignore")
        ),
        89: lambda: (
            (workspace / "gossipmesh" / "billing" / "plan_enforcement.py").is_file()
            and (workspace / "tests" / "test_plan_enforcement.py").is_file()
            and "PlanEnforcementService"
            in (workspace / "gossipmesh" / "billing" / "plan_enforcement.py").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        90: lambda: (
            (workspace / "gossipmesh" / "api" / "routers" / "billing.py").is_file()
            and (workspace / "tests" / "test_billing_permissions.py").is_file()
            and "require_billing_admin"
            in (workspace / "gossipmesh" / "api" / "routers" / "billing.py").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        92: lambda: (
            (workspace / "gossipmesh" / "billing" / "cost_controls.py").is_file()
            and (workspace / "tests" / "test_cost_controls.py").is_file()
            and "CostControlsEngine"
            in (workspace / "gossipmesh" / "billing" / "cost_controls.py").read_text(encoding="utf-8", errors="ignore")
        ),
        93: lambda: (
            (workspace / "gossipmesh" / "core" / "logging.py").is_file()
            and (workspace / "tests" / "test_structured_logging.py").is_file()
            and "StructuredJSONFormatter"
            in (workspace / "gossipmesh" / "core" / "logging.py").read_text(encoding="utf-8", errors="ignore")
        ),
        94: lambda: (
            (workspace / "gossipmesh" / "observability" / "metrics.py").is_file()
            and (workspace / "tests" / "test_observability_metrics.py").is_file()
            and "generate_latest_metrics"
            in (workspace / "gossipmesh" / "observability" / "metrics.py").read_text(encoding="utf-8", errors="ignore")
        ),
        95: lambda: (
            (workspace / "gossipmesh" / "observability" / "tracing.py").is_file()
            and (workspace / "tests" / "test_distributed_tracing.py").is_file()
            and "setup_tracer_provider"
            in (workspace / "gossipmesh" / "observability" / "tracing.py").read_text(encoding="utf-8", errors="ignore")
        ),
        96: lambda: (
            (workspace / "gossipmesh" / "api" / "routers" / "health.py").is_file()
            and (workspace / "tests" / "test_health_readiness.py").is_file()
            and "liveness_probe"
            in (workspace / "gossipmesh" / "api" / "routers" / "health.py").read_text(encoding="utf-8", errors="ignore")
        ),
        97: lambda: (
            (workspace / "docs" / "OPERATIONAL_RUNBOOKS.md").is_file()
            and "APIErrorRateHigh"
            in (workspace / "docs" / "OPERATIONAL_RUNBOOKS.md").read_text(encoding="utf-8", errors="ignore")
        ),
        98: lambda: (
            (workspace / "docs" / "DISASTER_RECOVERY.md").is_file()
            and (workspace / "gossipmesh" / "enterprise" / "disaster_recovery.py").is_file()
            and (workspace / "tests" / "test_disaster_recovery.py").is_file()
            and "DisasterRecoveryService"
            in (workspace / "gossipmesh" / "enterprise" / "disaster_recovery.py").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        99: lambda: (
            (workspace / "frontend" / "package.json").is_file()
            and (workspace / "frontend" / "src" / "app" / "layout.tsx").is_file()
            and (workspace / "frontend" / "src" / "lib" / "api.ts").is_file()
        ),
        100: lambda: (
            (workspace / "frontend" / "src" / "app" / "dashboard" / "page.tsx").is_file()
            and "Review Dashboard"
            in (workspace / "frontend" / "src" / "app" / "dashboard" / "page.tsx").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        101: lambda: (
            (workspace / "frontend" / "src" / "app" / "settings" / "page.tsx").is_file()
            and "Repository Settings"
            in (workspace / "frontend" / "src" / "app" / "settings" / "page.tsx").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        102: lambda: (
            (workspace / "frontend" / "src" / "app" / "findings" / "page.tsx").is_file()
            and "Human Feedback"
            in (workspace / "frontend" / "src" / "app" / "findings" / "page.tsx").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        103: lambda: (
            (workspace / "frontend" / "src" / "app" / "onboarding" / "page.tsx").is_file()
            and "Welcome to GossipMesh"
            in (workspace / "frontend" / "src" / "app" / "onboarding" / "page.tsx").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        104: lambda: (
            (workspace / "gossipmesh" / "notifications" / "service.py").is_file()
            and (workspace / "tests" / "test_notifications.py").is_file()
            and "NotificationDispatcher"
            in (workspace / "gossipmesh" / "notifications" / "service.py").read_text(encoding="utf-8", errors="ignore")
        ),
        105: lambda: (
            (workspace / "scripts" / "generate_sbom.py").is_file()
            and (workspace / "docs" / "DEPENDENCY_SECURITY.md").is_file()
            and (workspace / "tests" / "test_dependency_security.py").is_file()
        ),
        106: lambda: (
            (workspace / "gossipmesh" / "security" / "secret_scanner.py").is_file()
            and (workspace / "tests" / "test_secret_scanning.py").is_file()
            and "SecretScannerEngine"
            in (workspace / "gossipmesh" / "security" / "secret_scanner.py").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        107: lambda: (
            (workspace / "docs" / "FULL_THREAT_MODEL.md").is_file()
            and "THREAT-GH-01"
            in (workspace / "docs" / "FULL_THREAT_MODEL.md").read_text(encoding="utf-8", errors="ignore")
        ),
        108: lambda: (
            (workspace / "gossipmesh" / "audit" / "immutable_audit.py").is_file()
            and (workspace / "tests" / "test_immutable_audit.py").is_file()
            and "ImmutableAuditService"
            in (workspace / "gossipmesh" / "audit" / "immutable_audit.py").read_text(encoding="utf-8", errors="ignore")
        ),
        109: lambda: (
            (workspace / "gossipmesh" / "enterprise" / "disaster_recovery.py").is_file()
            and (workspace / "tests" / "test_data_export_and_deletion.py").is_file()
            and "purge_organization_data"
            in (workspace / "gossipmesh" / "enterprise" / "disaster_recovery.py").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        110: lambda: (
            (workspace / "docs" / "PRIVACY_AND_SECURITY.md").is_file()
            and "Customer Security Architecture"
            in (workspace / "docs" / "PRIVACY_AND_SECURITY.md").read_text(encoding="utf-8", errors="ignore")
        ),
        111: lambda: (
            (workspace / "gossipmesh" / "enterprise" / "break_glass.py").is_file()
            and (workspace / "tests" / "test_support_breakglass.py").is_file()
            and "BreakGlassControlService"
            in (workspace / "gossipmesh" / "enterprise" / "break_glass.py").read_text(encoding="utf-8", errors="ignore")
        ),
        112: lambda: (
            (workspace / "docs" / "SOC2_READINESS_CHECKLIST.md").is_file()
            and "SOC 2 Type II"
            in (workspace / "docs" / "SOC2_READINESS_CHECKLIST.md").read_text(encoding="utf-8", errors="ignore")
        ),
        113: lambda: (
            (workspace / "docker" / "Dockerfile.api").is_file()
            and (workspace / "docker" / "Dockerfile.worker").is_file()
            and (workspace / "docker" / "Dockerfile.frontend").is_file()
        ),
        114: lambda: (
            (workspace / "docker-compose.yml").is_file()
            and "pgvector" in (workspace / "docker-compose.yml").read_text(encoding="utf-8", errors="ignore")
        ),
        115: lambda: (
            (workspace / "k8s" / "deployment.yaml").is_file()
            and "HorizontalPodAutoscaler"
            in (workspace / "k8s" / "deployment.yaml").read_text(encoding="utf-8", errors="ignore")
        ),
        116: lambda: (
            (workspace / "terraform" / "main.tf").is_file()
            and (workspace / "terraform" / "variables.tf").is_file()
            and "aws_db_instance" in (workspace / "terraform" / "main.tf").read_text(encoding="utf-8", errors="ignore")
        ),
        117: lambda: (
            (workspace / "scripts" / "staging_smoke_test.py").is_file()
            and "run_staging_smoke_tests"
            in (workspace / "scripts" / "staging_smoke_test.py").read_text(encoding="utf-8", errors="ignore")
        ),
        118: lambda: (
            (workspace / "docs" / "RELEASE_PROCESS.md").is_file()
            and "Canary Rollout Strategy"
            in (workspace / "docs" / "RELEASE_PROCESS.md").read_text(encoding="utf-8", errors="ignore")
        ),
        119: lambda: (
            (workspace / "docs" / "STATUS_PAGE_AND_INCIDENTS.md").is_file()
            and "Incident Severity & Communication SLAs"
            in (workspace / "docs" / "STATUS_PAGE_AND_INCIDENTS.md").read_text(encoding="utf-8", errors="ignore")
        ),
        122: lambda: (
            (workspace / "tests" / "test_performance.py").is_file()
            and "test_concurrent_organization_usage_metering_throughput"
            in (workspace / "tests" / "test_performance.py").read_text(encoding="utf-8", errors="ignore")
        ),
        123: lambda: (
            (workspace / "tests" / "test_failure_injection.py").is_file()
            and "test_failure_injection_duplicate_webhook_idempotency"
            in (workspace / "tests" / "test_failure_injection.py").read_text(encoding="utf-8", errors="ignore")
        ),
        124: lambda: (
            (workspace / "gossipmesh" / "enterprise" / "feature_flags.py").is_file()
            and (workspace / "tests" / "test_feature_flags.py").is_file()
            and "FeatureFlagService"
            in (workspace / "gossipmesh" / "enterprise" / "feature_flags.py").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        125: lambda: (
            (workspace / "gossipmesh" / "enterprise" / "support_tooling.py").is_file()
            and (workspace / "tests" / "test_support_tooling.py").is_file()
            and "CustomerSupportTooling"
            in (workspace / "gossipmesh" / "enterprise" / "support_tooling.py").read_text(
                encoding="utf-8", errors="ignore"
            )
        ),
        126: lambda: (
            (workspace / "docs" / "GO_TO_MARKET_CHECKLIST.md").is_file()
            and "Target Customers"
            in (workspace / "docs" / "GO_TO_MARKET_CHECKLIST.md").read_text(encoding="utf-8", errors="ignore")
        ),
    }

    for task in tasks:
        # Check custom codebase heuristic
        if task.num in CODEBASE_CHECKS:
            try:
                if CODEBASE_CHECKS[task.num]():
                    task.status = "COMPLETED"
                    task.evidence = f"Codebase verification passed for Task {task.num}"
                    continue
            except Exception as e:
                import traceback

                print(f"[ERROR in CODEBASE_CHECKS for Task {task.num}]: {e}", file=sys.stderr)
                traceback.print_exc()

        # Check explicit Task <N> in merged PRs
        for pr_num, (pr_title, pr_head) in merged_prs.items():
            if f"task {task.num}" in pr_title.lower() or f"task-{task.num}" in pr_head.lower():
                task.status = "COMPLETED"
                task.evidence = f"Merged PR #{pr_num}: {pr_title}"
                break
        if task.status == "COMPLETED":
            continue

        # Check title token overlap against merged PRs
        t_stems = {w[:5] for w in re.findall(r"\w{4,}", task.name.lower())}
        for pr_num, (pr_title, pr_head) in merged_prs.items():
            pr_stems = {w[:5] for w in re.findall(r"\w{4,}", pr_title.lower())}
            overlap = t_stems & pr_stems
            if len(overlap) >= 2 or (len(t_stems) == 1 and overlap):
                task.status = "COMPLETED"
                task.evidence = f"Merged PR #{pr_num}: {pr_title}"
                break
        if task.status == "COMPLETED":
            continue

        # Check open PRs
        for pr_num, (pr_title, pr_head) in open_prs.items():
            if (
                f"task {task.num}" in pr_title.lower()
                or f"task-{task.num}" in pr_head.lower()
                or task.name.lower() in pr_title.lower()
            ):
                task.status = "IN_PROGRESS"
                task.evidence = f"Open PR #{pr_num}: {pr_title}"
                break
        if task.status != "PENDING":
            continue

        # Check open issues
        for iss_num, iss_title in open_issues.items():
            if f"task {task.num}" in iss_title.lower() or task.name.lower() in iss_title.lower():
                task.status = "IN_PROGRESS"
                task.evidence = f"Open Issue #{iss_num}: {iss_title}"
                break


def get_next_pending_task(tasks: List[PlanTask]) -> Optional[PlanTask]:
    """Returns the first task in sequential order that is strictly PENDING."""
    for task in tasks:
        if task.status == "PENDING":
            return task
    return None


def format_issue_content(task: PlanTask) -> Tuple[str, str]:
    """Formats issue title and Markdown body strictly conforming to the Jules plan standards."""
    title = f"feat(plan): Task {task.num} — {task.name}"
    body = f"""## 🚀 Enterprise SaaS Implementation Task: Task {task.num} — {task.name}

**Phase**: {task.phase}
**Specification Source**: `docs/ENTERPRISE_SAAS_IMPLEMENTATION_PLAN.md`

---

### 📋 Technical Specification
{task.spec}

---

### ⚙️ Jules Task Operating Rules & Mandate
> **Repository**: https://github.com/Aditya-9-6/GossipMesh
>
> Work only on this task. First inspect the existing repository and explain the relevant files. Do not rewrite unrelated code. Do not remove existing functionality without documenting a migration path. Add tests for all new behavior. Run the complete test suite before finishing. If the task cannot be safely completed, stop and explain why instead of creating fake implementations.

---

### 🛡️ Production Verification Criteria & Quality Checklist
- [ ] Implement real, concrete behavior rather than placeholders or stubs.
- [ ] Enforce strict tenant isolation, authorization, and data boundary controls.
- [ ] Ensure full protection of secrets, tokens, and credentials (zero leakage).
- [ ] Verify idempotency, durable retries, and clean error handling.
- [ ] Add comprehensive automated unit tests (`tests/test_*.py`) with complete pass status.
- [ ] Verify zero regressions in linting or typing (`ruff`, `mypy`).

---
*Created autonomously by GossipMesh Plan Advancement Engine*
"""
    return title, body


def create_github_issue(task: PlanTask, workspace: Path) -> Optional[int]:
    """Submits the task as a new GitHub issue and attaches auto-solve labels."""
    title, body = format_issue_content(task)
    cmd = [
        "gh",
        "issue",
        "create",
        "--repo",
        "Aditya-9-6/GossipMesh",
        "--title",
        title,
        "--body",
        body,
        "--label",
        "advancement,auto-solve,enterprise-plan",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=workspace)
    if res.returncode == 0:
        out = res.stdout.strip()
        print(f"[+] Successfully created GitHub Issue: {out}")
        # Extract issue number
        m = re.search(r"/issues/(\d+)", out)
        if m:
            return int(m.group(1))
    else:
        print(f"[!] Failed to create issue for Task {task.num}: {res.stderr}", file=sys.stderr)
    return None


def main():
    parser = argparse.ArgumentParser(description="GossipMesh Enterprise SaaS Plan Advancement Engine")
    parser.add_argument("--workspace", default=".", help="Workspace path")
    parser.add_argument("--status", action="store_true", help="Print status summary of all tasks")
    parser.add_argument("--next", action="store_true", help="Display next pending task without creating issue")
    parser.add_argument("--create-next", action="store_true", help="Create GitHub issue for the next pending task")
    parser.add_argument(
        "--solve-next", action="store_true", help="Create issue and trigger cloud AI solver immediately"
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=0,
        help="Batch create issues and dispatch AI solver for N pending tasks concurrently",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    tasks = parse_implementation_plan(workspace)
    audit_codebase_completion(tasks, workspace)

    completed = [t for t in tasks if t.status == "COMPLETED"]
    in_progress = [t for t in tasks if t.status == "IN_PROGRESS"]
    pending = [t for t in tasks if t.status == "PENDING"]

    print("===============================================================================")
    print("        GOSSIPMESH ENTERPRISE SAAS IMPLEMENTATION PLAN STATUS")
    print("===============================================================================")
    print(f" Total Tasks Defined:   {len(tasks)}")
    print(f" Completed Tasks:       {len(completed)} (verified in codebase & merged PRs)")
    print(f" In-Progress (PR/Issue): {len(in_progress)}")
    print(f" Remaining Pending:     {len(pending)}")
    print("===============================================================================\n")

    if args.status:
        for t in tasks:
            icon = "✅" if t.status == "COMPLETED" else ("⏳" if t.status == "IN_PROGRESS" else "⬜")
            ev = f" ({t.evidence})" if t.evidence else ""
            print(f"[{icon} {t.status:<11}] Task {t.num:>3}: {t.name}{ev}")
        return

    if args.batch > 0:
        batch_tasks = pending[: args.batch]
        if not batch_tasks:
            print("[INFO] No pending tasks available to batch-advance!")
            return

        print(f"🚀 Batch-advancing next {len(batch_tasks)} pending tasks in parallel...\n")
        dispatched = []
        for t in batch_tasks:
            print(f"[*] Creating GitHub Issue for Task {t.num} — {t.name}...")
            iss_num = create_github_issue(t, workspace)
            if iss_num:
                print(f"[*] Triggering AI Issue Solver Bot for Issue #{iss_num}...")
                subprocess.run(
                    [
                        "gh",
                        "workflow",
                        "run",
                        "ai-issue-solver.yml",
                        "--repo",
                        "Aditya-9-6/GossipMesh",
                        "-f",
                        f"issue_number={iss_num}",
                    ],
                    cwd=workspace,
                )
                dispatched.append((t.num, t.name, iss_num))
                print(f"[OK] Dispatched solver for Issue #{iss_num} (Task {t.num})\n")
            time.sleep(2)

        print("===============================================================================")
        print(f"🎉 Successfully dispatched {len(dispatched)} tasks concurrently:")
        for t_num, t_name, iss_num in dispatched:
            print(f"   - Task {t_num:>3}: {t_name} (Issue #{iss_num})")
        print("===============================================================================")
        return

    next_task = get_next_pending_task(tasks)
    if not next_task:
        print("[🎉 100% COMPLETE] All 127 tasks in the Enterprise SaaS Plan are completed!")
        sys.exit(0)

    print(f"🎯 Next Actionable Task: Task {next_task.num} — {next_task.name}")
    print(f"   Phase: {next_task.phase}")
    print(f"   Spec Preview: {next_task.spec[:160]}...\n")

    if args.create_next or args.solve_next:
        print(f"[*] Creating GitHub Issue for Task {next_task.num}...")
        iss_num = create_github_issue(next_task, workspace)
        if iss_num and args.solve_next:
            print(f"[*] Triggering AI Issue Solver Bot for Issue #{iss_num}...")
            subprocess.run(
                [
                    "gh",
                    "workflow",
                    "run",
                    "ai-issue-solver.yml",
                    "--repo",
                    "Aditya-9-6/GossipMesh",
                    "-f",
                    f"issue_number={iss_num}",
                ],
                cwd=workspace,
            )
            print(f"[OK] AI Issue Solver dispatched in cloud for Issue #{iss_num}!")


if __name__ == "__main__":
    main()
