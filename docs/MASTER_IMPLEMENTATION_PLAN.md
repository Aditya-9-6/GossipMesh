**GossipMesh is currently a strong prototype for autonomous code-review agents, but it is not yet a SaaS platform.** PR #9 was merged on **October 10, 2026** and added AST parsing, Gemini embeddings/RAG, and semantic caching. The next step is not adding isolated features; it requires converting the repository from local scripts and JSON files into a secure, multi-tenant, provider-neutral agent platform.

Important: no implementation plan can guarantee “Fortune 500 level” without execution, security review, legal compliance, load testing, and production operations. However, the plan below is the complete product and engineering blueprint I recommend using as the master implementation specification.

# GossipMesh Master Implementation Plan

## 1. Current repository assessment

### Current stack

- **Language:** Python 3.10+
- **Packaging:** `pyproject.toml`, setuptools
- **Testing:** `unittest`
- **External integrations:** Gemini REST API, Ollama, GitHub CLI
- **Persistence:** JSON files and JSONL ledgers
- **Runtime:** CLI commands and local automation scripts
- **CI:** Basic GitHub Actions test matrix for Python 3.10–3.12

### Current structure

```text
gossipmesh/
  node.py             Local file-backed gossip node and ledger
  memetic.py          Persistent architectural knowledge and scoring
  consensus.py        Multi-model vote aggregation
  red_team.py         Regex-based adversarial audit rules
  bridge.py           Go/Rust wire-contract code generation
  oracle.py           In-memory benchmark regression checks
  auction.py          Keyword-based agent specialty selection
  rag.py              Gemini embedding and JSON vector search
  semantic_cache.py   JSON semantic response cache
  cli.py              Local command-line interface
  __init__.py         Package exports

scripts/
  ai_issue_solver.py       AI issue implementation
  ai_pr_reviewer.py        PR review and consensus
  ai_ci_fixer.py           CI repair and code rewriting
  autonomous_loop.py       Issue-to-PR automation loop
  generate_advancement_issue.py
                           Automated issue generation

tests/
  test_gossipmesh.py       Main unit test suite

.github/workflows/
  ci.yml              Python test matrix

.gossip_mesh/
  Local cache, test artifacts, vector data, and ledger data
```

### How the current system works

The current execution model is local and file-based:

1. `autonomous_loop.py` finds or generates GitHub issues.
2. `ai_issue_solver.py` reads repository context and asks Gemini for complete file replacements.
3. The files are written directly to disk.
4. Tests and linting are executed.
5. `ai_pr_reviewer.py` gathers model votes, performs red-team checks, and writes review files.
6. `ai_ci_fixer.py` may rewrite files based on diagnostic logs.
7. The loop may create, push, review, and merge pull requests.

This is useful as a prototype, but it is not safe for untrusted SaaS workloads because there is no tenant isolation, durable database, authorization layer, policy engine, secure execution sandbox, provider abstraction, job queue, API service, billing system, audit architecture, or production observability.

---

# 2. Product definition

GossipMesh should become:

> A multi-tenant AI software-engineering automation platform that connects to a customer’s Git repositories, lets the customer bring their own AI provider keys, executes isolated analysis and coding workflows, and produces verifiable reviews, patches, tests, security findings, and pull requests.

## Core customer workflows

### A. AI pull-request review

- GitHub, GitLab, and Bitbucket integration
- Webhook-triggered review
- Incremental diff analysis
- Repository-aware RAG
- Security and quality analysis
- Test execution in a sandbox
- Inline review comments
- Confidence and evidence for every finding
- Human approval before code mutation

### B. Issue-to-PR implementation

- User selects an issue
- Agent generates an implementation plan
- User reviews the plan
- Agent creates an isolated workspace
- Agent writes code
- Agent executes tests
- Agent requests additional model reviews
- Agent opens a pull request
- User remains the final merge authority

### C. CI failure repair

- Ingest failed workflow logs
- Classify failure
- Reproduce failure in sandbox
- Generate candidate fix
- Run regression tests
- Produce a patch
- Require approval before pushing

### D. Repository intelligence

- Codebase indexing
- Architecture graph
- Dependency graph
- Historical PR and issue learning
- Security posture
- Ownership mapping
- Documentation search
- Technical debt discovery
- Change-impact analysis

### E. Organization governance

- Team workspaces
- Roles and permissions
- Approval policies
- Provider allowlists
- Data retention policies
- Audit logs
- SSO/SAML/OIDC
- SCIM provisioning
- Usage budgets
- Enterprise export and deletion

---

# 3. Target architecture

The current package should evolve into a modular monorepo.

```text
gossipmesh/
  api/
    app.py
    routes/
      auth.py
      organizations.py
      projects.py
      repositories.py
      agents.py
      runs.py
      reviews.py
      billing.py
      webhooks.py
      audit.py

  domain/
    users.py
    organizations.py
    projects.py
    repositories.py
    agents.py
    workflows.py
    runs.py
    findings.py
    providers.py
    usage.py
    policies.py

  application/
    commands/
    queries/
    services/
    workflows/
    policies/

  agents/
    base.py
    planner.py
    reviewer.py
    security.py
    test_runner.py
    fixer.py
    summarizer.py
    researcher.py
    coordinator.py

  providers/
    base.py
    registry.py
    gemini.py
    openai.py
    anthropic.py
    ollama.py
    openrouter.py
    azure_openai.py
    bedrock.py
    vertex_ai.py

  orchestration/
    graph.py
    state_machine.py
    scheduler.py
    retries.py
    budgets.py
    approvals.py
    checkpoints.py
    cancellation.py

  retrieval/
    indexer.py
    chunker.py
    embeddings.py
    reranker.py
    vector_store.py
    code_graph.py
    hybrid_search.py

  execution/
    sandbox.py
    container_runner.py
    command_policy.py
    artifact_store.py
    patch_applier.py
    test_runner.py
    resource_limits.py

  integrations/
    github.py
    gitlab.py
    bitbucket.py
    slack.py
    jira.py
    linear.py
    sentry.py

  security/
    secrets.py
    encryption.py
    authorization.py
    redaction.py
    prompt_injection.py
    supply_chain.py
    ssrf.py
    path_policy.py

  persistence/
    database.py
    repositories.py
    migrations/
    models/

  observability/
    logging.py
    metrics.py
    tracing.py
    events.py

  contracts/
    schemas.py
    errors.py
    versioning.py

  cli/
    main.py
    commands/

scripts/
  migrate_legacy_data.py
  index_repository.py
  run_worker.py
  run_api.py
  run_security_scan.py

tests/
  unit/
  integration/
  contract/
  security/
  e2e/
  performance/
  fixtures/

deploy/
  docker/
  kubernetes/
  terraform/
  helm/

docs/
  architecture/
  security/
  operations/
  api/
  product/
```

---

# 4. Phase 0: Stabilize the current codebase

This phase is mandatory before adding major features.

## Fix broken or dangerous implementation details

### `scripts/ai_issue_solver.py`

Fix:

- Incorrect Gemini hostname: `generativelanguage.pyogleapis.com`
- Incorrect documentation URLs containing `pyogle`
- Duplicate and contradictory system-prompt sections
- References to Go conventions inside a Python project
- Unused `keywords` variable
- Hardcoded complete-file replacement behavior
- No schema validation of AI output
- No protection against writing outside the workspace
- No patch preview or approval step
- No file size limits
- No response size limits
- No structured error types
- No provider abstraction

### `scripts/ai_ci_fixer.py`

Fix:

- Incorrect Gemini hostname
- Untrusted AI-generated paths written directly to disk
- No path traversal protection
- No maximum number of modified files
- No maximum file size
- No patch validation
- No diff review before applying files
- No rollback if a generated patch damages the workspace
- Diagnostics use misleading Go terminology
- `black` and `flake8` are optional but failures are not handled consistently
- AI can rewrite tests and implementation without approval
- No command allowlist
- No sandbox

### `scripts/ai_pr_reviewer.py`

Fix:

- The model is queried twice per loop iteration.
- Consensus votes and detailed audit calls are mixed together.
- The prompt schema contains duplicate JSON keys.
- The generated JSON schema is not validated.
- `safe_auto_fixes` and `auto_patch` have overlapping behavior.
- The reviewer may set a success status when confidence is low.
- Review output is written into the repository working tree.
- The script can automatically invoke a fixer and push changes.
- It assumes `origin/main` exists.
- It relies on `gh` being installed and authenticated.
- It contains stale references to unrelated systems.
- It uses API keys through query parameters.
- It lacks budget, timeout, cancellation, and per-run limits.

### `scripts/autonomous_loop.py`

This file must not remain an unrestricted production control plane.

Replace:

- Global API key rotation
- Automatic branch force-pushing
- `--admin` merge behavior
- Shell command construction
- Human authorization through substring matching such as `"/merge"`
- Infinite loop without cancellation
- Repository-specific hardcoded constants
- Direct local checkout mutation
- Concurrent workflow collision risk
- Lack of idempotency
- Lack of job ownership and locks

with:

- Durable job queue
- Explicit workflow state machine
- Idempotency keys
- User approval records
- Restricted GitHub installation tokens
- Worker isolation
- Lease-based job locks
- Dead-letter queue
- Retry policies
- Cancellation signals
- Audit events

### `gossipmesh/node.py`

The current local JSONL ledger is not a production gossip network.

Replace or isolate:

- Shared filesystem synchronization
- Full-ledger rescans on every sync
- Unlocked append operations
- Unlocked ledger rewrites
- Silent exception swallowing
- Mutable callback execution
- No message authentication
- No peer authentication
- No real network transport
- No durable offsets
- No payload size limits
- No schema versioning
- No encryption

Implement:

- Event envelopes
- Message signatures
- Hash chaining
- Sequence numbers
- Idempotent event ingestion
- Topic authorization
- Durable event offsets
- PostgreSQL-backed event store
- Redis or NATS event distribution
- Peer identity
- Replay protection
- Payload schemas
- Dead-letter handling

### `gossipmesh/rag.py`

Replace the prototype vector database.

Current limitations:

- Stores all content and vectors in one JSON file.
- Indexes only Python files.
- Takes only the first 15,000 characters.
- No chunking strategy.
- No file hash invalidation.
- No deleted-file cleanup.
- No tenant or repository isolation.
- No access-control filtering.
- O(N) similarity scan.
- Gemini-only embeddings.
- API key errors are printed.
- Raw source content is stored without encryption.

Implement:

- Tree-sitter or language-server-based parsing
- Chunking by symbol and semantic boundaries
- File and chunk hashes
- Incremental indexing
- Hybrid lexical plus vector search
- PostgreSQL with pgvector or a managed vector store
- Metadata filters
- Repository and branch scoping
- Permission-aware retrieval
- Reranking
- Context compression
- Citation metadata
- Index versioning
- Re-index jobs
- Embedding provider abstraction
- Local embedding fallback
- Deletion and retention policies

### `gossipmesh/semantic_cache.py`

Replace with a production cache layer:

- Redis-backed cache
- Tenant-scoped keys
- Provider/model/version-scoped keys
- Prompt-template versioning
- TTL and eviction
- Approximate nearest-neighbor search
- Cache poisoning protection
- PII and secret redaction before caching
- Usage and hit-rate metrics
- Explicit cache invalidation
- No raw API key or sensitive repository data in cache identifiers

### `gossipmesh/consensus.py`

The current system is weighted voting, not full Byzantine fault tolerance.

Implement:

- Registered model/provider identities
- Signed vote envelopes
- Duplicate-vote prevention
- Run-level vote membership
- Model failure handling
- Quorum policies per workflow
- Risk-weighted approval
- Mandatory deterministic checks
- Human override rules
- Conflict explanation
- Evidence references
- Abstention handling
- Minimum independent-provider requirements
- Model diversity controls
- Cost-aware quorum policies

Do not represent a single model called multiple times as independent Byzantine nodes.

### `gossipmesh/red_team.py`

The current regex detector is useful as a prototype but insufficient for security.

Implement:

- Python AST analysis
- Tree-sitter multi-language analysis
- Semgrep integration
- Bandit
- CodeQL integration
- Secret scanning
- Dependency vulnerability scanning
- IaC scanning
- Container scanning
- SSRF analysis
- Prompt-injection detection
- Deserialization checks
- SQL injection checks
- Command injection checks
- Path traversal checks
- Auth and authorization checks
- Taint tracking
- SARIF output
- Severity calibration
- False-positive suppression with audit history

### `gossipmesh/oracle.py`

Persist benchmark data and make regression analysis statistically valid:

- Benchmark artifacts
- Baseline selection
- Commit and branch association
- Environment metadata
- Confidence intervals
- Variance detection
- Warm-up runs
- Repeated measurements
- Threshold policies
- Per-service budgets
- Historical dashboards
- No unconditional zero-allocation rule for every Python path

### `gossipmesh/auction.py`

Replace keyword-only bidding with capability-based scheduling:

- Agent capability registry
- Historical success rate
- Cost per task
- Latency
- Provider availability
- Security clearance
- Required tools
- Language support
- Repository permissions
- Current load
- Failure rate
- Budget constraints
- User-selected policies

### `gossipmesh/memetic.py`

Replace local mutable JSON knowledge with governed organizational memory:

- Evidence-backed knowledge records
- Source PR, commit, issue, and test references
- Confidence scores
- Expiration dates
- Tenant ownership
- Approval state
- Contradiction detection
- Human review
- Version history
- Deletion and retention
- No direct prompt injection without trust classification

---

# 5. Phase 1: Provider-neutral AI platform

The user must own and select their AI provider keys.

## Provider interface

Create:

```python
class ModelProvider(Protocol):
    async def generate(
        self,
        request: CompletionRequest,
        *,
        cancellation_token: CancellationToken,
    ) -> CompletionResponse:
        ...

    async def embed(
        self,
        request: EmbeddingRequest,
        *,
        cancellation_token: CancellationToken,
    ) -> EmbeddingResponse:
        ...

    async def health(self) -> ProviderHealth:
        ...
```

## Providers to support

Initial release:

- OpenAI
- Anthropic
- Google Gemini
- Azure OpenAI
- Ollama
- OpenRouter

Enterprise expansion:

- AWS Bedrock
- Google Vertex AI
- Mistral
- Cohere
- Self-hosted vLLM
- Custom OpenAI-compatible endpoints

## Key ownership model

Users should be able to choose:

1. **BYOK:** user supplies their own provider key.
2. **Organization key:** organization administrator supplies a shared key.
3. **Self-hosted provider:** user supplies an internal endpoint.
4. **Platform-managed provider:** optional future offering, if legally and commercially desired.

## Secret requirements

- Encrypt keys using envelope encryption.
- Use KMS-backed data-encryption keys.
- Never place keys in URLs.
- Never log keys.
- Never store raw keys in job payloads.
- Decrypt only inside the provider adapter.
- Store only masked fingerprints for display.
- Support rotation and revocation.
- Record provider usage without recording secret values.
- Apply per-user and per-organization budgets.
- Prevent agents from accessing provider credentials directly.

---

# 6. Phase 2: SaaS control plane

Create an API service using FastAPI or another production ASGI framework.

## Required services

### API service

Responsible for:

- Authentication
- Authorization
- Organization management
- Repository connections
- Agent configuration
- Workflow creation
- Run status
- Approvals
- Usage
- Billing
- Audit logs

### Worker service

Responsible for:

- Indexing
- Repository cloning
- Code analysis
- Model calls
- Test execution
- Patch generation
- Review generation
- Artifact creation

### Scheduler

Responsible for:

- Queuing jobs
- Retries
- Backoff
- Dead-letter jobs
- Per-tenant concurrency
- Priority
- Cancellation
- Timeouts

### Event service

Responsible for:

- Webhooks
- Internal events
- Agent progress
- Notifications
- WebSocket or SSE streaming

### Web application

Recommended stack:

- React
- Next.js
- TypeScript
- Tailwind
- Accessible component system
- Secure session handling
- Organization-aware routing

## Required backend dependencies

Use carefully selected production dependencies:

- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- Celery, Dramatiq, Arq, or Temporal
- OpenTelemetry
- Structlog
- Pytest
- Hypothesis
- Ruff
- MyPy or Pyright

Avoid adding dependencies merely for perceived sophistication.

---

# 7. Multi-tenancy model

Every resource must have an explicit tenant boundary.

## Core entities

```text
User
Organization
Membership
Role
Project
RepositoryConnection
RepositoryBranch
Agent
AgentRun
Workflow
WorkflowStep
ProviderCredential
ProviderModel
PromptTemplate
KnowledgeDocument
KnowledgeChunk
Finding
Patch
Artifact
Approval
UsageEvent
BillingSubscription
AuditEvent
Webhook
Integration
Policy
```

## Required tenant rules

- Every database record has `organization_id` where applicable.
- Every query is tenant-scoped.
- Every object access checks authorization.
- Repository data cannot cross organizations.
- Vector search is filtered by organization and repository.
- Caches are tenant-scoped.
- Artifacts are tenant-scoped.
- Logs use tenant-safe correlation IDs.
- Background jobs carry tenant context.
- Support personnel use audited break-glass access.
- Data export and deletion are tenant-specific.

---

# 8. Authentication and authorization

Implement:

- Email/password authentication only if necessary
- OIDC login
- GitHub OAuth
- Google Workspace login
- SAML SSO for enterprise
- SCIM provisioning
- MFA
- Session rotation
- Device/session management
- Passwordless login
- API keys for automation
- Personal access tokens with scopes
- Organization roles
- Project roles
- Repository-level permissions
- Approval permissions
- Billing permissions
- Audit-log permissions

Use a policy engine or centralized authorization service rather than scattered `if` statements.

Example roles:

```text
Owner
Billing Administrator
Organization Administrator
Security Administrator
Developer
Reviewer
Auditor
Read-only Analyst
Service Account
```

---

# 9. Agent system design

The agent should be a state machine, not a collection of scripts.

## Standard workflow

```text
CREATED
  -> AUTHORIZED
  -> PLANNING
  -> CONTEXT_RETRIEVAL
  -> ANALYSIS
  -> SPECIALIST_REVIEW
  -> SECURITY_REVIEW
  -> TEST_PLAN
  -> SANDBOX_EXECUTION
  -> PATCH_GENERATION
  -> PATCH_VALIDATION
  -> HUMAN_APPROVAL
  -> PULL_REQUEST_CREATION
  -> POST_PR_MONITORING
  -> COMPLETED
```

Every transition must be:

- Persisted
- Idempotent
- Audited
- Retryable
- Cancellable
- Time-limited
- Tenant-scoped

## Agent roles

### Coordinator

- Owns the workflow
- Dispatches specialist agents
- Enforces budgets
- Handles failures
- Never directly edits files

### Planner

- Creates implementation plan
- Identifies affected files
- Produces risk map
- Defines acceptance criteria

### Repository researcher

- Searches code
- Builds architecture context
- Finds similar historical changes
- Produces citations

### Reviewer

- Identifies correctness issues
- Produces severity-ranked findings
- Must cite exact file and line evidence

### Security agent

- Performs security analysis
- Runs static scanners
- Detects secrets and unsafe behavior
- Blocks high-risk changes

### Test agent

- Determines required tests
- Runs existing tests
- Generates missing test proposals
- Detects flaky tests

### Patch agent

- Produces a patch, not unrestricted file replacement
- Modifies only authorized paths
- Preserves formatting and interfaces
- Produces a diff summary

### Verification agent

- Runs tests and static analysis
- Checks patch scope
- Confirms issue acceptance criteria
- Compares before and after behavior

### Human approval agent

Not an AI model. This is a policy boundary requiring a user or authorized reviewer.

---

# 10. Secure code execution

This is the most important missing capability.

Never run customer repository code directly inside the API server or ordinary worker process.

## Sandbox requirements

Use isolated ephemeral environments with:

- Rootless containers or microVMs
- Read-only base image
- Temporary writable workspace
- No host filesystem access
- No Docker socket
- No cloud metadata access
- Restricted outbound network
- DNS filtering
- CPU limits
- Memory limits
- Disk limits
- Process limits
- Wall-clock timeout
- File-count limits
- Output-size limits
- Syscall restrictions
- Non-root user
- Automatic cleanup
- Artifact quarantine

## Command policy

Every command must be:

- Explicitly allowed
- Logged
- Associated with a workflow step
- Time-limited
- Resource-limited
- Reproducible

Default-deny dangerous commands:

```text
sudo
mount
umount
docker
podman
kubectl
terraform apply
git push
git reset --hard
rm -rf /
curl with arbitrary shell execution
wget with arbitrary shell execution
ssh
scp
credential-store access
```

A user may explicitly authorize additional commands through a policy.

---

# 11. Patch safety

The AI must never directly replace arbitrary files.

Implement a patch pipeline:

```text
AI output
  -> JSON schema validation
  -> path validation
  -> patch parser
  -> allowed-file check
  -> maximum-change check
  -> secret scan
  -> syntax validation
  -> formatting
  -> unit tests
  -> security tests
  -> diff summary
  -> human approval
  -> isolated branch commit
```

Rules:

- Reject absolute paths.
- Reject `..` traversal.
- Reject symlink escapes.
- Reject binary files unless explicitly allowed.
- Reject changes outside the task scope.
- Reject generated secrets.
- Reject modifications to CI permissions without approval.
- Reject changes to authentication code without elevated approval.
- Reject changes to billing code without elevated approval.
- Reject large unexplained diffs.
- Preserve the original workspace.
- Support rollback.

---

# 12. Git provider integration

Implement a provider interface:

```python
class SourceControlProvider(Protocol):
    async def get_repository(...): ...
    async def get_pull_request(...): ...
    async def create_branch(...): ...
    async def create_commit(...): ...
    async def create_pull_request(...): ...
    async def create_review(...): ...
    async def add_comment(...): ...
    async def get_workflow_logs(...): ...
```

Initial implementations:

- GitHub App integration
- GitLab OAuth/application integration
- Bitbucket integration

Use installation tokens with minimum permissions.

Avoid:

- User-owned global PATs
- `gh pr merge --admin`
- Force pushing by default
- Shelling out to the GitHub CLI for core product functionality
- Parsing comments as authorization commands

---

# 13. API surface

Minimum REST endpoints:

```text
POST   /v1/auth/login
POST   /v1/auth/logout
GET    /v1/me

GET    /v1/organizations
POST   /v1/organizations
GET    /v1/organizations/{org_id}
PATCH  /v1/organizations/{org_id}

GET    /v1/projects
POST   /v1/projects
GET    /v1/projects/{project_id}

POST   /v1/repositories/connect
GET    /v1/repositories
POST   /v1/repositories/{id}/index
GET    /v1/repositories/{id}/index-status

POST   /v1/provider-credentials
GET    /v1/provider-credentials
DELETE /v1/provider-credentials/{id}
POST   /v1/provider-credentials/{id}/rotate
POST   /v1/provider-credentials/{id}/test

GET    /v1/agents
POST   /v1/agents
PATCH  /v1/agents/{id}

POST   /v1/runs
GET    /v1/runs
GET    /v1/runs/{id}
POST   /v1/runs/{id}/cancel
POST   /v1/runs/{id}/approve
POST   /v1/runs/{id}/reject
GET    /v1/runs/{id}/events
GET    /v1/runs/{id}/artifacts

GET    /v1/findings
GET    /v1/findings/{id}
POST   /v1/findings/{id}/resolve
POST   /v1/findings/{id}/suppress

GET    /v1/usage
GET    /v1/audit-events
GET    /v1/policies
PATCH  /v1/policies

POST   /v1/webhooks/github
POST   /v1/webhooks/gitlab
POST   /v1/webhooks/bitbucket
```

Use versioned APIs and generate OpenAPI documentation.

---

# 14. Database design

Use PostgreSQL as the system of record.

## Required properties

- UUID primary keys
- Tenant-scoped unique constraints
- Foreign-key integrity
- Soft deletion where appropriate
- Created and updated timestamps
- Optimistic locking
- Migration history
- Audit metadata
- Encryption for sensitive columns
- Query indexes
- Row-level security where practical
- Transaction boundaries

## Do not store in Git

Remove generated runtime artifacts from source control:

```text
.gossip_mesh/cache/*
.gossip_mesh/test_cache/*
.gossip_mesh/vectordb.json
.gossip_mesh/audit_logs/*
```

Use object storage, database tables, or ephemeral job storage instead.

---

# 15. Observability

Implement production observability before launch.

## Logs

- Structured JSON logs
- Correlation ID
- Organization ID
- Project ID
- Workflow ID
- Agent ID
- Provider name
- Model name
- Latency
- Token counts
- Cost estimates
- Result status
- Redacted error details

Never log:

- API keys
- Access tokens
- Full source files
- Full prompts by default
- Credentials
- Private repository data outside tenant scope

## Metrics

Track:

- Workflow success rate
- Review latency
- Queue latency
- Provider error rate
- Token usage
- Cost per run
- Cache hit rate
- RAG retrieval quality
- Test pass rate
- Patch acceptance rate
- False-positive rate
- False-negative discoveries
- Sandbox failures
- Human approval rate
- Tenant usage
- API error rate
- Database latency

## Tracing

Use OpenTelemetry across:

- API
- Queue
- Agent steps
- Provider calls
- Retrieval
- Sandbox execution
- Git integrations

---

# 16. Evaluation and quality system

Do not rely on model scores alone.

## Build an evaluation dataset

Include:

- Real historical PRs
- Known security vulnerabilities
- Buggy patches
- Correct patches
- False-positive examples
- Multi-language repositories
- Large repositories
- Monorepos
- Generated code
- Secret-containing test fixtures
- Prompt-injection fixtures
- Malicious repository fixtures

## Measure

- Finding precision
- Finding recall
- Severity accuracy
- Patch success rate
- Test preservation rate
- Review latency
- Cost per review
- Human acceptance rate
- Regression rate
- Security escape rate
- Retrieval relevance
- Citation correctness

## Release gates

A release must not proceed if:

- High-severity security tests fail.
- Tenant isolation tests fail.
- Secret leakage tests fail.
- Sandbox escape tests fail.
- Unauthorized repository access is possible.
- Provider credentials appear in logs.
- Patch scope validation can be bypassed.
- Critical workflows have no rollback.

---

# 17. Security program

Implement a real security program, not only regex checks.

## Required controls

- Threat model
- Secure development lifecycle
- Dependency pinning
- Dependabot or Renovate
- SBOM generation
- Container image scanning
- Secret scanning
- SAST
- DAST
- IaC scanning
- License scanning
- Signed releases
- Reproducible builds
- Branch protection
- Required reviews
- Protected environments
- Key rotation
- Backup encryption
- Disaster recovery
- Incident response plan
- Vulnerability disclosure policy
- Security contact
- Penetration tests
- Annual third-party assessment

## Compliance roadmap

Depending on target customers:

1. Security baseline
2. SOC 2 readiness
3. SOC 2 Type I
4. SOC 2 Type II
5. GDPR readiness
6. CCPA/CPRA readiness
7. ISO 27001 readiness
8. Enterprise procurement package
9. HIPAA only if healthcare data is intentionally supported
10. FedRAMP only if pursuing government customers

Do not claim compliance before an independent assessment.

---

# 18. Billing and SaaS economics

Implement platform billing independently from customer AI spend.

## Billing dimensions

- Organization subscription
- Number of developers
- Number of repositories
- Number of reviewed pull requests
- Number of agent runs
- Sandbox compute time
- Repository index size
- Retention period
- Enterprise support
- SSO and compliance features

## BYOK billing model

The customer pays AI provider costs directly. GossipMesh charges for:

- Platform access
- Workflow execution
- Storage
- Indexing
- Sandbox compute
- Enterprise controls
- Support

Track usage independently from provider responses.

## Required billing features

- Stripe integration
- Plans
- Trials
- Seats
- Metered usage
- Invoices
- Tax handling
- Webhook verification
- Subscription state machine
- Grace periods
- Usage caps
- Billing admin role
- Exportable invoices

---

# 19. Frontend product requirements

The SaaS dashboard should include:

### Overview

- Organization health
- Active workflows
- Recent findings
- Usage
- Cost estimates
- Provider health

### Repository page

- Branches
- Index status
- Last synchronization
- Architecture map
- Security posture
- Recent reviews
- Configuration

### Run page

- Live progress
- Agent steps
- Retrieved evidence
- Provider/model selection
- Token and cost usage
- Test logs
- Sandbox artifacts
- Findings
- Approval controls

### Finding page

- Severity
- Confidence
- Exact source location
- Evidence
- Explanation
- Suggested fix
- Reproduction
- Related history
- Suppression workflow

### Organization settings

- Members
- Roles
- SSO
- Providers
- Policies
- Retention
- Billing
- Audit logs
- Webhooks
- Data export/deletion

---

# 20. CI/CD improvements

Expand `.github/workflows/ci.yml` into separate workflows:

```text
ci.yml
security.yml
typecheck.yml
format.yml
unit-tests.yml
integration-tests.yml
e2e-tests.yml
build-images.yml
dependency-review.yml
release.yml
database-migrations.yml
```

Required checks:

```bash
python -m compileall gossipmesh scripts
ruff check .
ruff format --check .
mypy gossipmesh
pytest -q
pytest tests/security -q
pytest tests/integration -q
pip-audit
bandit -r gossipmesh scripts
```

Add:

- Coverage threshold
- Mutation testing
- Dependency review
- SBOM
- Secret scanning
- Container scanning
- Preview environments
- Migration verification
- Rollback tests
- Release signing

---

# 21. Testing strategy

The current single `unittest` file is not enough.

## Unit tests

Cover:

- Domain models
- Authorization policies
- Provider adapters
- Retry logic
- State transitions
- Cache behavior
- Chunking
- Retrieval
- Patch validation
- Redaction
- Budget enforcement
- Consensus
- Audit events

## Integration tests

Cover:

- PostgreSQL
- Redis
- Object storage
- Provider mocks
- Git provider mocks
- Webhooks
- Background workers
- Database migrations
- Tenant isolation

## Security tests

Cover:

- SSRF
- Path traversal
- Command injection
- Prompt injection
- Secret leakage
- Unauthorized repository access
- Cross-tenant vector retrieval
- Sandbox escape attempts
- Malicious Git repositories
- Symlink attacks
- Archive bombs
- Oversized files
- Malformed webhook signatures

## End-to-end tests

Cover:

- Organization creation
- Repository connection
- Indexing
- PR review
- Issue-to-PR workflow
- User approval
- Rejection
- Cancellation
- Retry
- Billing event
- Data deletion

## Property-based tests

Use Hypothesis for:

- Event serialization
- Vector clock behavior
- Patch paths
- Policy evaluation
- State-machine transitions
- Input size boundaries

---

# 22. Migration plan from current prototype

## Keep and adapt

- `gossipmesh.consensus`
- `gossipmesh.auction`
- `gossipmesh.bridge`
- `gossipmesh.red_team`
- `gossipmesh.oracle`
- Parts of `gossipmesh.memetic`
- Parts of `gossipmesh.rag`
- Parts of AST extraction in `ai_pr_reviewer.py`

## Deprecate

- Direct JSON ledger as the primary data store
- Shared Google Drive fallback
- Hardcoded `G:/My Drive`
- Global key rotation
- Local cache as source of truth
- Shell-driven GitHub automation
- Automatic admin merge
- Regex-only security audits
- Full-file AI rewrites
- Infinite autonomous loop
- Human commands detected by comment substring
- Unauthenticated gossip messages

## Compatibility layer

Create adapters so existing CLI commands continue to work:

```text
gossipmesh status
gossipmesh broadcast
gossipmesh memes
gossipmesh audit
```

The CLI should call the same application services used by the SaaS API, not duplicate business logic.

---

# 23. Recommended delivery sequence

## Milestone 1: Production safety baseline

- Fix broken API URLs.
- Remove hardcoded paths.
- Add typed configuration.
- Add structured errors.
- Add logging and redaction.
- Add path-safe patch application.
- Disable automatic merge.
- Add test coverage.
- Add Ruff, MyPy, Pytest.
- Remove generated artifacts from Git.

## Milestone 2: Core platform foundation

- FastAPI API.
- PostgreSQL.
- Alembic migrations.
- Redis.
- Background workers.
- Organization and user models.
- Authentication.
- Authorization.
- Audit events.
- Provider credential encryption.

## Milestone 3: Provider abstraction

- Provider interface.
- Gemini adapter.
- OpenAI adapter.
- Anthropic adapter.
- Ollama adapter.
- Model selection policies.
- Usage accounting.
- Provider health checks.
- Key rotation.

## Milestone 4: Secure agent runtime

- Workflow state machine.
- Agent registry.
- Durable jobs.
- Cancellation.
- Budgets.
- Sandboxed execution.
- Artifact storage.
- Patch approval pipeline.

## Milestone 5: Repository intelligence

- GitHub App.
- Repository sync.
- Incremental indexing.
- Symbol-level chunking.
- Hybrid retrieval.
- Architecture graph.
- Citation-backed context.

## Milestone 6: PR review product

- Webhook handling.
- Review orchestration.
- Security findings.
- Test execution.
- Inline comments.
- Review reports.
- Human approval workflow.

## Milestone 7: Issue solver and CI fixer

- Plan-first workflow.
- Patch generation.
- Reproduction.
- Regression testing.
- User approval.
- PR creation.
- No automatic merge by default.

## Milestone 8: Enterprise controls

- SSO.
- SCIM.
- Advanced roles.
- Data retention.
- Data export.
- Regional deployment.
- Audit exports.
- Compliance program.

## Milestone 9: Billing and commercialization

- Stripe.
- Plans.
- Metered usage.
- Seat management.
- Platform fees.
- Enterprise contracts.
- Usage dashboards.

## Milestone 10: Scale and reliability

- Kubernetes or managed container platform.
- Horizontal worker scaling.
- Queue partitioning.
- Rate limiting.
- Multi-region readiness.
- Disaster recovery.
- Load testing.
- Chaos testing.
- SLOs and error budgets.

---

# 24. Non-negotiable product principles

1. **AI never receives unrestricted production credentials.**
2. **AI never pushes or merges code without explicit policy authorization.**
3. **Every model-generated finding must include evidence.**
4. **Every code mutation must produce a reviewable diff.**
5. **Every workflow must be resumable and cancellable.**
6. **Every customer resource must be tenant-isolated.**
7. **Every provider call must be budgeted and observable.**
8. **Every sandbox must be isolated from the host.**
9. **Every security finding must be reproducible where possible.**
10. **Every automated decision must be explainable and auditable.**
11. **Customer data must never be used for training by default.**
12. **BYOK credentials must never appear in logs, URLs, prompts, or artifacts.**
13. **Human approval must remain configurable but available for high-risk actions.**
14. **The platform must fail closed for security-sensitive operations.**
15. **A model score is not a security control.**

---

# 25. Definition of “production ready”

GossipMesh should not be marketed as an enterprise SaaS platform until all of these are true:

- Multi-tenant database exists.
- Tenant isolation is tested automatically.
- API authentication and authorization are complete.
- Provider keys are encrypted and rotated.
- GitHub App integration replaces broad PAT usage.
- Sandboxed code execution is implemented.
- Patch scope is validated.
- Automatic admin merges are removed.
- All model output is schema-validated.
- Workflows are durable and resumable.
- Security scanning is integrated.
- Audit logs are immutable or tamper-evident.
- Backups and disaster recovery are tested.
- Rate limits and budgets are enforced.
- CI includes security, integration, and end-to-end tests.
- Observability dashboards exist.
- Billing is tested with webhook replay protection.
- Data deletion works.
- Privacy documentation exists.
- Incident response procedures exist.
- A third-party security review has been completed.

---

# 26. Final recommendation

Do **not** continue expanding the current scripts as if they were already a SaaS foundation. The correct strategy is:

1. Freeze the current prototype.
2. Fix all correctness and security defects.
3. Extract reusable domain logic from the scripts.
4. Build the API, database, worker, and sandbox foundation.
5. Add provider-neutral BYOK support.
6. Implement repository integrations.
7. Build durable agent workflows.
8. Add the dashboard and billing system.
9. Run security, performance, and adversarial evaluations.
10. Launch first as a controlled developer beta.
11. Expand into enterprise only after tenant isolation, auditability, and operational reliability are proven.

The existing modules provide useful ideas, especially consensus, memetic knowledge, RAG, red-team analysis, and agent specialization. But they should become components inside a governed SaaS platform rather than remain independent local scripts.

Save this specification as:

```text
docs/MASTER_IMPLEMENTATION_PLAN.md
```

The most urgent implementation order is:

```text
security fixes
→ typed configuration
→ API and database
→ authentication and tenancy
→ provider abstraction
→ job orchestration
→ sandbox
→ Git provider integration
→ RAG/indexing
→ agent workflows
→ dashboard
→ billing
→ enterprise compliance
```

Without that order, adding more agent intelligence will increase risk faster than it increases product value.