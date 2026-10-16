# GossipMesh Enterprise SaaS Implementation Plan

**Repository:** `Aditya-9-6/GossipMesh`  
**Status:** Prototype with active autonomous issue-to-PR automation  
**Target:** Sellable, secure, multi-tenant AI software-engineering SaaS

> This plan is intentionally staged. Do not give Jules the entire plan as one task. Assign one task at a time, review the diff, run tests, and only then continue.

## Current position

GossipMesh already processes approximately 30+ issues per day, generates pull requests, and performs automated review. That proves the automation has practical value. It does **not** by itself prove production or enterprise readiness.

The first commercial product should be a controlled AI pull-request review and issue-to-PR platform with:

- GitHub App integration
- Organization and repository isolation
- Durable background jobs
- Human approval before code mutation
- Evidence-based review findings
- Secure sandbox execution
- Usage limits and billing
- Audit logs and operational observability

Automatic merge, unrestricted shell execution, unrestricted AI file replacement, and cross-tenant data access must remain disabled by default.

## Jules task operating rules

Use this preamble with every Jules task:

```text
Repository: https://github.com/Aditya-9-6/GossipMesh

Work only on this task. First inspect the existing repository and explain the relevant files. Do not rewrite unrelated code. Do not remove existing functionality without documenting a migration path. Add tests for all new behavior. Run the complete test suite before finishing. If the task cannot be safely completed, stop and explain why instead of creating fake implementations.
```

After every task, assign this review prompt:

```text
Review the implementation as a production engineer.

Check:
- Did you implement real behavior rather than placeholders?
- Are tenant boundaries enforced?
- Are secrets protected?
- Are retries and idempotency handled?
- Are errors observable?
- Are tests meaningful?
- Did you introduce security regressions?
- Did you modify unrelated files?

Run the complete test suite and report:
1. changed files
2. tests run
3. test results
4. security risks
5. remaining TODOs
6. the exact next recommended task
```

---

# Phase 0 — Immediate safety and stabilization

These tasks should be completed first because the current automation can modify files, push branches, and interact with GitHub.

## Task 1 — Production-readiness baseline

Create `docs/PRODUCTION_READINESS.md`. Audit API functionality, authentication, authorization, multi-tenancy, database design, jobs, webhook security, AI security, sandboxing, observability, billing, deployment, testing, and compliance. Mark each category complete, partial, prototype, or missing with exact file evidence.

## Task 2 — Accurate README

Rewrite `README.md` so implemented, prototype, and planned features are clearly separated. Remove unsupported claims and link to the architecture and readiness documents.

## Task 3 — Engineering standards

Add or update `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.editorconfig`, pre-commit configuration, development setup, secret-handling rules, test requirements, and commit conventions.

## Task 4 — Pytest and coverage

Add pytest, pytest-asyncio, coverage configuration, reusable fixtures, test markers, and test-environment configuration while preserving existing unittest tests.

## Task 5 — Ruff and typing

Add Ruff and MyPy or Pyright. Fix high-priority errors without blindly suppressing diagnostics. Add CI commands.

## Task 6 — CI quality gates

Improve `.github/workflows/ci.yml` with unit tests, integration tests, linting, type checking, coverage thresholds, dependency scanning, and secret scanning. CI must fail on real errors.

## Task 7 — Remove misleading terminology

Audit prompts, scripts, and documentation for incorrect Go, Rust, proxy, or unrelated-system claims. Replace misleading terminology without removing valid bridge functionality.

## Task 8 — Safety flags and kill switch

Add environment-controlled flags:

- `GOSSIPMESH_AUTOMATION_ENABLED`
- `GOSSIPMESH_ALLOW_PR_CREATION`
- `GOSSIPMESH_ALLOW_PUSH`
- `GOSSIPMESH_ALLOW_FORCE_PUSH`
- `GOSSIPMESH_ALLOW_AUTO_MERGE`
- `GOSSIPMESH_MAX_FILES_PER_CHANGE`
- `GOSSIPMESH_MAX_DAILY_RUNS`
- `GOSSIPMESH_MAX_DAILY_PR_CREATION`

Default PR creation, push, force-push, and auto-merge to disabled. Apply checks in all autonomous scripts and add tests.

## Task 9 — Dry-run mode

Add `--dry-run` to autonomous workflows. Dry-run may inspect, analyze, generate a proposed diff, and validate, but must not write source files, create branches, push, create PRs, comment, or merge.

## Task 10 — Generated patch validation

Before applying AI-generated changes, validate relative paths, workspace containment, symlink escapes, forbidden files, file count, file size, total diff size, UTF-8, Python syntax, JSON schema, and authorized paths.

## Task 11 — Durable run tracking

Track repository, issue, PR, workflow type, run ID, status, timestamps, failure reason, branch, commit SHA, files changed, model, token usage, and estimated cost. Prevent duplicate issue and PR processing.

## Task 12 — Issue-to-PR idempotency

Repeated execution must not create duplicate branches, PRs, commits, comments, usage charges, or workflows. Check active runs, existing PRs, prior attempts, branch state, and generated commit identity.

## Task 13 — Human approval gate

Require explicit approval before pushing commits, creating PRs, posting final reviews, or applying generated patches. Store approver, timestamp, approved commit/diff, and expiration.

## Task 14 — Change-risk classifier

Classify changes as LOW, MEDIUM, HIGH, or CRITICAL based on file count, line count, sensitive directories, auth changes, migrations, dependencies, infrastructure, shell scripts, security code, and test changes. Require approval for MEDIUM+ and block CRITICAL by default.

## Task 15 — Daily cost and volume limits

Track and enforce per-repository and per-organization limits for AI runs, PRs, tokens, estimated cost, changed lines, and sandbox minutes.

## Task 16 — Automation outcome report

Persist daily and weekly metrics: issues processed, PRs created, CI pass rate, merged/rejected/reverted PRs, review scores, false positives, cost, latency, and approval rate. Expose them through CLI or API.

## Task 17 — Canary mode

Allow automation only for selected repositories and labels, with daily limits, human approval, no force-push, no auto-merge, separate metrics, and immediate shutdown.

## Task 18 — Disable unsafe defaults

Make automatic merge, automatic push, arbitrary command execution, full-file replacement, and unapproved patch application disabled by default. Add regression tests proving this.

---

# Phase 1 — Architecture and API foundations

## Task 19 — Architecture document

Create `docs/ARCHITECTURE.md` for API, webhooks, auth, authorization, PostgreSQL, Redis, queues, workers, sandboxing, AI providers, indexing, review generation, audit logs, billing, and observability. Mark implemented versus planned components.

## Task 20 — Layered architecture

Refactor one vertical slice, preferably PR review, into API, application service, domain, infrastructure, worker, and integration layers. Add import-boundary tests.

## Task 21 — Structured errors

Create typed errors and consistent FastAPI responses for auth, authorization, validation, provider, GitHub, database, job, sandbox, and rate-limit failures. Redact sensitive information.

## Task 22 — API schemas

Add explicit Pydantic request and response models to all routes. Remove public raw dictionaries, declare response models, standardize validation errors, and add contract tests.

## Task 23 — Request correlation IDs

Add request IDs to response headers, structured logs, jobs, audit events, and error responses. Never use arbitrary user input as identity.

## Task 24 — API documentation

Make OpenAPI accurate, version API contracts, document authentication, errors, rate limits, pagination, and webhook behavior.

---

# Phase 2 — Database and persistence

## Task 25 — Model audit

Audit SQLAlchemy models for foreign keys, indexes, uniqueness, cascades, timestamps, status constraints, nullable fields, tenant ownership, and relationship loading.

## Task 26 — PostgreSQL system of record

Replace production-relevant JSON, JSONL, and in-memory persistence for workflows, jobs, findings, audits, provider metadata, repository connections, reviews, and usage with database-backed storage.

## Task 27 — Alembic migrations

Create reliable initial and incremental migrations. Add upgrade/downgrade tests and prevent destructive startup migrations.

## Task 28 — Transaction boundaries

Make workflow state changes, usage records, audit events, approvals, and billing state changes transactionally safe. Add rollback tests.

## Task 29 — Optimistic concurrency

Add versioning or optimistic locking for workflows, jobs, approvals, repository connections, and mutable tenant resources.

## Task 30 — Soft deletion and retention

Add `deleted_at`, deletion actors, retention metadata, tenant-scoped deletion, audit events, and default query filtering.

## Task 31 — Database indexes and query audit

Profile common queries and add indexes for organization, repository, workflow, job, status, timestamps, and idempotency keys. Add query regression tests.

## Task 32 — Database backup validation

Document and test PostgreSQL backups, point-in-time recovery, restore procedures, encryption keys, and tenant exports.

---

# Phase 3 — Multi-tenancy and authorization

## Task 33 — Tenant model

Complete organizations, memberships, roles, projects, repository connections, ownership, membership status, and invitations.

## Task 34 — Centralized authorization

Implement a policy service for organization, project, repository, billing, audit, approval, and service-account permissions. Add positive and negative authorization tests.

## Task 35 — Tenant-scoped queries

Audit every database query and prevent cross-organization access to records, source data, embeddings, caches, artifacts, logs, and audit events.

## Task 36 — Organization APIs

Implement organization creation, invitations, acceptance, membership removal, role assignment, suspension, and audit logging.

## Task 37 — Project and repository APIs

Implement project creation, repository connection, branch selection, repository removal, and repository policy configuration.

## Task 38 — Service accounts and API keys

Implement hashed, scoped, expiring, revocable organization API keys. Display full keys only once and record usage.

## Task 39 — Rate limiting

Add Redis-backed, organization-aware limits for login, API, webhooks, reviews, indexing, provider calls, and expensive jobs.

## Task 40 — Cross-tenant security tests

Create a dedicated test suite proving users, workers, caches, RAG, artifacts, logs, and jobs cannot cross tenant boundaries.

---

# Phase 4 — Authentication and enterprise identity

## Task 41 — Password security

Add password strength validation, secure reset tokens, login throttling, lockout or progressive delays, inactive-user handling, and password-change session invalidation.

## Task 42 — JWT and sessions

Implement short-lived access tokens, rotating refresh tokens, reuse detection, revocation, issuer/audience validation, clock skew handling, and session management.

## Task 43 — GitHub App or OAuth

Implement secure GitHub authentication with state validation, PKCE where applicable, token storage, organization mapping, minimal scopes, and audit events.

## Task 44 — OIDC

Implement provider-neutral OIDC with discovery, authorization code flow, PKCE, nonce, claims mapping, organization mapping, account linking, and mocked-provider tests.

## Task 45 — SAML boundary

Implement a secure SAML integration boundary with organization configuration, metadata validation, certificate handling, login/logout, and audit events. Do not create fake SSO behavior.

## Task 46 — SCIM 2.0

Implement organization-scoped user provisioning, updates, deprovisioning, filtering, pagination, authentication, role mapping, and audit events.

## Task 47 — MFA

Implement optional organization-enforced TOTP MFA, recovery codes, enrollment, challenge, rotation, admin enforcement, and audit events.

## Task 48 — Enterprise roles

Implement Owner, Billing Administrator, Organization Administrator, Security Administrator, Developer, Reviewer, Auditor, Analyst, and Service Account roles with documented permissions.

---

# Phase 5 — GitHub integration and webhooks

## Task 49 — Durable webhook ingestion

Implement raw-body signature verification, delivery ID tracking, idempotency, payload limits, durable receipts, retry processing, dead-letter handling, and installation mapping.

## Task 50 — GitHub App installations

Implement installation registration, repository selection, minimal permissions, token generation, expiration handling, permission validation, removal, and audit logs.

## Task 51 — Repository lifecycle

Support connect, permission verification, branch selection, disconnect, reconnect, rename, archive, and installation-change behavior.

## Task 52 — PR diff retrieval

Retrieve PR metadata, files, diff, base/head SHAs, commits, status, and renames with pagination, timeouts, retries, rate-limit handling, and mocked tests.

## Task 53 — Inline review comments

Create evidence-backed inline comments with file, line, side, commit SHA, severity, finding fingerprint, duplicate prevention, grouping, and partial failure handling.

## Task 54 — Webhook replay

Create an admin-only event replay mechanism that uses the normal idempotent processing pipeline and audits the replay actor.

## Task 55 — GitHub permissions audit

Verify every GitHub API operation uses the minimum required permission and document the permission matrix.

## Task 56 — GitHub failure handling

Implement resilient handling for revoked installations, deleted repositories, rate limits, permissions errors, API outages, and changed default branches.

---

# Phase 6 — Workflow engine and background jobs

## Task 57 — Durable queue

Replace FastAPI `BackgroundTasks` for long-running work with a durable queue using Celery, Dramatiq, Arq, or another justified system. Add persistence, retries, visibility timeout, dead letters, and cancellation.

## Task 58 — Workflow state machines

Implement persisted PR review, indexing, issue solving, and CI repair state machines with validated transitions, auditing, idempotency, retries, cancellation, and deadlines.

## Task 59 — Idempotency keys

Add idempotency keys to workflow creation, webhook jobs, comments, PR creation, usage, billing, and artifact operations.

## Task 60 — Cancellation and timeouts

Implement user/admin cancellation, provider timeout, sandbox timeout, overall deadlines, cancellation checks, cleanup, and final state recording.

## Task 61 — Per-tenant concurrency

Limit active reviews, indexing, sandbox jobs, provider calls, and worker capacity per organization with fairness and priority.

## Task 62 — Retry policies

Categorize transient and permanent failures. Use exponential backoff and dead letters without retrying invalid input or authorization failures forever.

## Task 63 — Worker ownership and leases

Implement worker identity, job leases, lease expiry, recovery after worker crash, and duplicate execution prevention.

## Task 64 — Scheduler and priorities

Implement scheduled indexing, queued reviews, priority rules, customer plan limits, and graceful shutdown.

---

# Phase 7 — AI providers and review quality

## Task 65 — Provider-neutral interface

Define typed interfaces for generation, structured JSON, embeddings, health, token usage, errors, cancellation, and timeouts. Implement Gemini first.

## Task 66 — Additional providers

Add adapters for OpenAI, Anthropic, Azure OpenAI, Ollama, OpenRouter, Bedrock, Vertex AI, or compatible endpoints without coupling business logic to one provider.

## Task 67 — AI response validation

Use Pydantic schemas for verdict, severity, confidence, paths, lines, evidence, remediation, citations, and usage. Reject malformed or unsafe output.

## Task 68 — Secure provider clients

Remove API keys from URLs where possible, redact keys from logs and exceptions, add timeouts, retries, circuit breakers, and safe provider errors.

## Task 69 — AI budgets

Track provider, model, tokens, cost, workflow, repository, organization, and timestamp. Enforce daily/monthly budgets and pause over-budget jobs.

## Task 70 — Prompt construction

Create a structured prompt pipeline with repository context, changed files, symbols, policies, accepted/dismissed findings, evidence requirements, and output schemas. Isolate untrusted repository content from system instructions.

## Task 71 — Finding normalization

Add stable finding fingerprints, source, category, severity, confidence, evidence, explanation, remediation, file, line range, and duplicate detection.

## Task 72 — Deterministic review gates

Integrate secret scanning, dependency scanning, Bandit or equivalent, linting, formatting, tests, and changed-file policies. Critical deterministic findings cannot be overridden by AI approval.

## Task 73 — Review quality evaluation

Build an evaluation dataset and measure precision, recall, false positives, severity accuracy, duplicate rate, latency, cost, dismissals, and reverts.

## Task 74 — Human feedback learning

Persist accepted, dismissed, false-positive, reopened, and corrected findings. Use this feedback for evaluation and safe prompt improvements, not uncontrolled prompt injection.

---

# Phase 8 — Repository indexing and RAG

## Task 75 — Production vector storage

Replace JSON vectors with PostgreSQL/pgvector or a justified managed vector database. Store organization, repository, branch, file, chunk, hash, provider, version, deletion, and retention metadata.

## Task 76 — Incremental indexing

Index changed files only, remove deleted files, track commits and hashes, version index jobs, report progress, support retry and cancellation.

## Task 77 — Symbol-aware chunking

Use AST or tree-sitter symbol boundaries. Store file paths, symbols, line ranges, commit SHA, and citations. Design an extensible multi-language interface.

## Task 78 — Permission-aware retrieval

Enforce organization, project, repository, branch, and user permissions during retrieval. Add cross-tenant negative tests.

## Task 79 — Hybrid search and reranking

Combine lexical and vector search with metadata filtering, reranking, context limits, duplicate removal, deterministic ordering, and citations.

## Task 80 — Secure cache

Replace file cache with tenant-scoped Redis cache, TTL, model/provider/version keys, prompt versioning, invalidation, size limits, PII/secret redaction, poisoning protection, and metrics.

---

# Phase 9 — Secure code execution

## Task 81 — Sandbox threat model

Create `docs/SECURITY_SANDBOX.md` covering malicious code, dependency attacks, exfiltration, credential theft, escapes, fork bombs, resource exhaustion, prompt injection, and artifact poisoning.

## Task 82 — Deny-by-default command policy

Allow only explicitly approved commands with workflow association, logging, time limits, resource limits, and validated arguments. Reject shell-string execution.

## Task 83 — Isolated execution adapter

Use rootless containers or microVMs with non-root users, read-only base images, temporary workspaces, no host filesystem, no Docker socket, restricted network, CPU/memory/disk/process limits, timeouts, output limits, and cleanup.

## Task 84 — Artifact quarantine

Implement tenant-scoped artifact storage with size/type validation, malware-scanning integration, retention, authorization, download auditing, and cleanup.

## Task 85 — Sandbox escape tests

Test path traversal, symlink escapes, environment leakage, metadata access, network access, process/memory/disk exhaustion, dangerous commands, and artifact manipulation.

## Task 86 — Dependency and network policy

Define allowed package registries, dependency caching, network egress rules, lockfile requirements, and offline or restricted test modes.

---

# Phase 10 — Billing and commercialization

## Task 87 — Real Stripe integration

Replace the in-memory billing class with customer creation, checkout, subscriptions, billing portal, cancellation, invoices, signature-verified webhooks, idempotency, and test mode.

## Task 88 — Usage metering

Durably meter reviewed PRs, changed lines, tokens, indexing, sandbox minutes, seats, storage, and premium scanners. Make records immutable and idempotent.

## Task 89 — Plan enforcement

Implement free trial, free, team, business, and enterprise plans with seats, repositories, monthly usage, feature flags, overages, and grace periods.

## Task 90 — Billing permissions

Restrict billing APIs to billing administrators. Audit invoices, payment methods, subscriptions, plan changes, usage, and cancellation.

## Task 91 — Enterprise contracts

Model annual contracts, custom limits, purchase orders, invoicing, negotiated plans, and contract-specific enforcement without fake payment behavior.

## Task 92 — Cost controls

Add provider cost alerts, organization budget alerts, emergency shutdown, and cost anomaly detection.

---

# Phase 11 — Observability and operations

## Task 93 — Structured logging

Replace prints with structured logs containing service, environment, request ID, workflow ID, job ID, organization ID where safe, event, duration, and error category. Redact secrets and source code.

## Task 94 — Metrics

Add metrics for requests, latency, errors, webhooks, workflow duration, queue depth, retries, provider latency/failures, tokens, findings, sandbox failures, and billing usage.

## Task 95 — Distributed tracing

Add OpenTelemetry across API, webhooks, workflows, queues, GitHub, providers, database, and sandbox. Do not include secrets or raw source code in trace attributes.

## Task 96 — Health and readiness

Add liveness, readiness, database, Redis, worker, provider, and migration status endpoints without exposing secrets.

## Task 97 — Alerts and runbooks

Document alert thresholds and runbooks for API errors, queue backlog, job failures, provider outage, webhook failures, database saturation, sandbox failures, cost anomalies, and authorization violations.

## Task 98 — Disaster recovery

Document and test backups, restore, RPO, RTO, encryption key recovery, artifact recovery, tenant export, tenant deletion, and incident communication.

---

# Phase 12 — Frontend and customer product

## Task 99 — SaaS web application

Create a Next.js/TypeScript frontend with login, organization selection, dashboard, repositories, review runs, findings, settings, members, billing, and audit logs.

## Task 100 — Review dashboard

Show recent PRs, status, findings, severity, processing time, provider usage, failures, dismissals, accepted findings, and loading/error/unauthorized states.

## Task 101 — Repository settings

Add branch selection, review rules, severity thresholds, provider settings, indexing status, ignored paths, and security policies.

## Task 102 — Human feedback UI

Support finding acceptance, dismissal, false-positive marking, comments, reopening, and patch approval with persistent audit history.

## Task 103 — Onboarding

Implement account creation, organization creation, GitHub App installation, repository selection, policy setup, first review, trial/billing, and recovery from incomplete onboarding.

## Task 104 — Customer notifications

Add email, Slack, or webhook notifications for review completion, critical findings, failed jobs, approvals, usage limits, and billing events.

---

# Phase 13 — Security, compliance, and legal readiness

## Task 105 — Dependency security

Automate vulnerability scans, fix critical/high issues, generate an SBOM if practical, and document risk acceptance and upgrade policy.

## Task 106 — Secret scanning

Scan source, history where appropriate, tests, logs, artifacts, and configuration. Use fake credentials in fixtures.

## Task 107 — Full threat model

Threat-model GitHub, webhooks, auth, tenants, AI, RAG, prompt injection, sandbox, billing, support access, artifacts, and jobs. Map threats to mitigations and tests.

## Task 108 — Immutable audit events

Audit login, failures, roles, repository connections, provider credentials, reviews, findings, approvals, sandbox work, exports, deletions, billing, and support access.

## Task 109 — Data export and deletion

Implement authorized asynchronous exports and deletion for users, repositories, source indexes, reviews, findings, artifacts, usage, and retention-governed logs.

## Task 110 — Privacy and customer security docs

Create privacy data flow, customer security, subprocessors, retention, incident response, and deletion documentation. Do not claim certifications prematurely.

## Task 111 — Support break-glass controls

Require explicit reason, authorization, expiry, least privilege, and audit logging for support access. Never expose source code by default.

## Task 112 — SOC 2 readiness checklist

Map access control, change management, vulnerability management, logging, incidents, backups, vendors, employee access, retention, and deletion to evidence requirements.

---

# Phase 14 — Deployment and releases

## Task 113 — Production Docker images

Create minimal non-root images for API, worker, scheduler, and frontend with pinned dependencies, health checks, and reproducible builds.

## Task 114 — Production-like Compose

Create local Compose for PostgreSQL, Redis, API, worker, scheduler, frontend, and optional object storage with health checks and persistence.

## Task 115 — Deployment manifests

Document and create deployment manifests for secrets, database, Redis, workers, API, ingress, TLS, autoscaling, migrations, object storage, monitoring, and network policies.

## Task 116 — Infrastructure as code

Create Terraform or equivalent for network, database, Redis, object storage, secrets manager, workloads, monitoring, and backups with dev/staging/prod separation.

## Task 117 — Staging environment

Create staging configuration, secrets, deployment pipeline, smoke tests, migration checks, rollback, and test GitHub App integration.

## Task 118 — Release process

Add versioning, changelog, migration policy, staging approval, backups, rollback, feature flags, canary rollout, and post-release verification.

## Task 119 — Status page and incident communication

Define service status, incident severity, customer communication, postmortems, and status-page integration.

---

# Phase 15 — Quality and launch

## Task 120 — Integration tests

Cover auth, tenant isolation, webhooks, repository connection, workflows, retries, provider failures, review persistence, billing, and auditing.

## Task 121 — End-to-end PR review test

Test webhook receipt, signature verification, idempotent workflow creation, queueing, diff retrieval, deterministic checks, mocked AI, finding validation, persistence, comments, and audit events.

## Task 122 — Performance tests

Load-test webhook ingestion, review creation, indexing, retrieval, database queries, queue throughput, and concurrent organizations. Define targets and record results.

## Task 123 — Failure-injection tests

Test GitHub, provider, database, Redis, worker, duplicate webhook, cancellation, sandbox, and billing failures. Verify retries, cleanup, and final states.

## Task 124 — Feature flags

Add organization-scoped flags for review, scanning, indexing, issue solving, CI fixing, patch generation, sandboxing, and beta providers. Support emergency disablement.

## Task 125 — Customer support tooling

Provide authorized lookup, health inspection, failed workflow retry, audit inspection, and export initiation with break-glass controls.

## Task 126 — Go-to-market checklist

Create `docs/GO_TO_MARKET_CHECKLIST.md` covering target customers, pricing, trial, support, uptime, status page, terms, privacy, DPA, subprocessors, security questionnaire, incident response, refunds, analytics, and demo environment.

## Task 127 — Final production review

Review all critical blockers, tenant isolation, auth, webhooks, jobs, sandbox, AI validation, billing, observability, backups, deployment, documentation, tests, and incident response. Produce a release decision based on evidence. Never mark production-ready without passing evidence.

---

# Recommended milestone order

## Internal alpha

Complete Tasks 1–18, 19–32, 33–40, 57–64, 65–74, 93–98, and 124.

## Sellable PR-review beta

Complete Tasks 41–56, 75–80, 99–104, 113–121, and 126.

The first paid product should focus on:

- GitHub App installation
- Secure webhook processing
- Organization accounts
- Repository-aware AI PR review
- Evidence-backed inline findings
- Human approval
- Usage limits
- Audit logs

Do not enable automatic merge in the first paid version.

## Enterprise edition

Complete Tasks 45–48, 81–92, 105–112, 115–119, and 122–127.

# Product strategy

Start with:

> Secure, evidence-based AI pull-request review for engineering teams.

Then add:

1. Repository intelligence and historical context
2. CI failure diagnosis
3. Human-approved patch generation
4. Issue-to-PR automation
5. Enterprise self-hosting or private deployment
6. BYOK and local-model support

Measure quality using accepted PRs, rejected PRs, reverted PRs, false positives, cost per review, latency, and customer retention. Do not use PR volume as the primary success metric.

# Definition of enterprise-ready

Do not call the system enterprise-ready until it has evidence for:

- No known critical tenant-isolation vulnerability
- Durable and idempotent workflows
- Human-controlled code mutation
- Secure sandbox execution
- Least-privilege GitHub integration
- SSO/SAML/OIDC and SCIM where promised
- Centralized authorization
- Immutable audit events
- Encrypted and governed customer data
- Tested backups and recovery
- Real billing and usage enforcement
- Observability and incident response
- Repeatable security and performance testing
- Accurate customer-facing documentation

# Suggested first Jules task

Begin with Task 1, then Task 8, then Tasks 9–13. These provide the fastest reduction in operational risk while preserving your current 30+ issue/day automation.
