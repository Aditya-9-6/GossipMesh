# Remaining Implementation Plan for Milestones 1 to 7

This document outlines the detailed plan to complete the remaining foundational milestones (1 through 7) based on the `docs/MASTER_IMPLEMENTATION_PLAN.md`.

## Execution Strategy
These milestones represent the transition from a local prototype to a production SaaS. They must be executed sequentially, as each builds upon the last.

## Milestone 1: Production safety baseline
1. **Fix broken API URLs:** Review `gossipmesh/` and `scripts/` to ensure no hardcoded or broken API URLs exist.
2. **Remove hardcoded paths:** Replace paths like `G:/My Drive` with dynamic configuration driven paths or environment variables (`GOSSIPMESH_DIR`).
3. **Add typed configuration:** Implement `gossipmesh/core/config.py` using `pydantic.BaseSettings` for type-safe environment variable management.
4. **Structured Errors & Logging:** Introduce a centralized logging configuration in `gossipmesh/core/logging.py` and custom exception classes.
5. **Path-safe patch application:** Ensure `ai_pr_reviewer.py` and `ai_issue_solver.py` strictly validate file paths before applying diffs.
6. **Disable automatic merge:** Remove code that automatically merges PRs based on string matching (e.g. `/merge`).
7. **CI/CD setup:** Add `ruff`, `mypy`, and `pytest` configurations to `pyproject.toml` and `.github/workflows`.

## Milestone 2: Core platform foundation
1. **FastAPI Setup:** Initialize the main API application in `gossipmesh/api/main.py` and mount routers.
2. **PostgreSQL & SQLAlchemy:** Set up `gossipmesh/db/session.py` and base models in `gossipmesh/models/base.py`. Define `Organization` and `User` models.
3. **Alembic:** Initialize alembic for database migrations (`alembic init alembic`).
4. **Redis & Background Workers:** Configure Celery in `gossipmesh/worker/celery_app.py` for asynchronous task processing.
5. **Auth & Security:** Implement JWT authentication and Role-Based Access Control (RBAC) in `gossipmesh/api/dependencies.py`.
6. **Audit Events:** Create an `AuditEvent` database model to replace local file logs.
7. **Encryption:** Implement symmetric encryption (e.g., using `cryptography.fernet`) for storing provider credentials in the database.

## Milestone 3: Provider abstraction
1. **Provider Interface:** Create an abstract base class `BaseProvider` in `gossipmesh/providers/base.py`.
2. **Adapters:** Implement specific adapters for `GeminiProvider`, `OpenAIProvider`, `AnthropicProvider`, and `OllamaProvider`.
3. **Manager:** Implement `ProviderManager` to handle model routing, fallback policies, and usage accounting.
4. **Integration:** Update existing code (`gossipmesh/consensus.py`, `scripts/ai_pr_reviewer.py`) to use the `ProviderManager` instead of direct API calls.

## Milestone 4: Secure agent runtime
1. **Models:** Define `Workflow`, `Job`, `Budget`, and `Artifact` models in `gossipmesh/models/runtime.py`.
2. **State Machine:** Implement a durable state machine for workflow transitions (Pending -> Running -> Awaiting Approval -> Completed/Failed).
3. **Agent Registry:** Create a registry for specialized agents (Security, Performance, Architect).
4. **Sandbox execution:** Integrate a secure sandbox mechanism (e.g., Docker containerization or gVisor) in `gossipmesh/runtime/sandbox.py` to isolate agent-generated code execution.

## Milestone 5: Repository intelligence
1. **GitHub App:** Implement GitHub App authentication (OAuth/Installation Tokens) to replace Personal Access Tokens (PATs).
2. **Indexing & Chunking:** Refactor `gossipmesh/rag.py` into a proper pipeline (`indexing.py`, `chunking.py`) using `pgvector` for vector storage instead of JSON.
3. **Retrieval:** Implement a `HybridRetriever` that combines semantic search (pgvector) with the `NetworkX` architecture graph.

## Milestone 6: PR review product
1. **Webhooks:** Create FastAPI endpoints in `gossipmesh/api/routers/webhooks.py` to handle GitHub PR events.
2. **Review Orchestration:** Wrap the logic from `scripts/ai_pr_reviewer.py` into a Celery task `tasks.pr_review_task`.
3. **Reporting:** Post structured review comments back to the GitHub PR using the GitHub App API.

## Milestone 7: Issue solver and CI fixer
1. **Issue Solver Workflow:** Wrap `scripts/ai_issue_solver.py` into a state-managed workflow. Ensure it generates a plan, requests approval, and produces a patch.
2. **CI Fixer Workflow:** Wrap `scripts/ai_ci_fixer.py` to respond to failed CI build webhook events.
3. **PR Creation:** Ensure the workflows open a reviewable PR rather than committing directly to main/master branches.
