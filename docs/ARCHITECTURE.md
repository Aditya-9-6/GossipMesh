# GossipMesh Target Production Architecture

This document describes the target production architecture for GossipMesh as it transitions into a secure, multi-tenant AI agent SaaS platform. It covers key components, their purpose, and their current implementation status.

## 1. API Service
**Status:** Partially Implemented

The core control plane is built using FastAPI. It exposes RESTful endpoints to handle incoming requests, manage organizations, users, and orchestrate the AI workflows. Current implementation includes basic endpoints, while future iterations will expand the API to cover the entire platform management.

## 2. Webhooks
**Status:** Partially Implemented

Webhooks are crucial for integrating with external platforms like GitHub. The platform receives events (e.g., Pull Request opened, Issue created) via webhooks. Currently, there is an endpoint (`gossipmesh/api/webhooks.py`) to process GitHub payloads and trigger background tasks. Secure signature validation and idempotent processing are being implemented.

## 3. Authentication
**Status:** Planned

The system requires robust authentication to secure API access. While basic token mechanisms exist, the target architecture mandates integrating OIDC and GitHub OAuth for secure user and organization sign-in, moving away from simple passwords.

## 4. Authorization
**Status:** Planned

A centralized authorization layer will ensure that all actions are tenant-scoped. Every query and data access must verify permissions against the user's roles within an organization. A policy engine will replace scattered `if` statements, enforcing rules like rejecting unauthorized changes to CI or billing code.

## 5. PostgreSQL
**Status:** Partially Implemented

PostgreSQL serves as the primary system of record, storing relational data (Users, Organizations, Repositories, Workflows, Jobs). SQLAlchemy 2.0 with Alembic is used for ORM and schema migrations. The base models and session management are in place, but multi-tenant data isolation constraints are actively being developed.

## 6. Redis
**Status:** Partially Implemented

Redis is used for caching, rate limiting, and pub/sub message distribution. Currently, some caching logic (`gossipmesh/db/redis.py`) is implemented. The target state will use Redis as a robust caching layer for API responses, tenant-scoped keys, and provider/model caching to reduce latency and redundant LLM API calls.

## 7. Job Queue
**Status:** Partially Implemented

Asynchronous workflows (e.g., PR reviews, codebase indexing) are offloaded to a job queue. While FastAPI `BackgroundTasks` are used currently, a Celery-based worker setup (`gossipmesh/worker/celery_app.py`) is being introduced to ensure durable, scalable, and resilient background task execution.

## 8. Worker Service
**Status:** Partially Implemented

The worker service consumes tasks from the job queue. These workers execute the heavy lifting: running AI workflows, querying LLMs, and performing repository analysis. The foundations are laid out, but full horizontal scalability and robust error handling/retries are under active development.

## 9. Sandbox Execution
**Status:** Partially Implemented

To safely run untrusted code or execute AI-generated scripts, a secure sandbox environment is required. The `gossipmesh/runtime/sandbox.py` provides isolation, ensuring AI agents cannot access sensitive host environment variables or perform arbitrary file modifications on the platform infrastructure.

## 10. AI Provider Adapters
**Status:** Implemented

A unified abstraction layer allows GossipMesh to interface with multiple LLM providers seamlessly. The `ProviderManager` and specific adapters for OpenAI, Anthropic, Gemini, and Ollama (`gossipmesh/providers/`) are fully implemented, allowing flexible model routing (Tier 1 vs Tier 2).

## 11. Repository Indexing
**Status:** Implemented

Codebases must be indexed to provide context to the AI models. This involves AST-based symbol chunking, hybrid retrieval (lexical + vector search), and architecture graph generation (`gossipmesh/repository/`). The RAG system uses pgvector-backed indexing to find relevant code snippets for PR reviews and issue solving.

## 12. Review Generation
**Status:** Implemented

The AI-driven PR review generation workflow is functional. Orchestrated via `gossipmesh/workflows/pr_review.py`, it analyzes diffs, queries the indexed repository for context, evaluates changes against memetic architectural rules, and automatically posts review comments back to the source control system.

## 13. GitHub Integration
**Status:** Partially Implemented

Integration with GitHub is necessary to read repository data, post comments, and merge PRs. Currently, it relies on webhook parsing and API calls (`gossipmesh/repository/github.py`). The planned transition involves shifting from broad Personal Access Tokens (PATs) to a more granular and secure GitHub App model.

## 14. Audit Logging
**Status:** Planned

Comprehensive audit logging is required for enterprise compliance and security. Every significant action (e.g., policy changes, PR merges, user access) must be recorded immutably. The base audit models (`models/audit.py`) exist, but the robust logging architecture is planned.

## 15. Billing
**Status:** Planned

The platform will feature a multi-dimensional billing system, charging for platform usage (compute, storage, MAUs) independently of the AI provider costs (BYOK model). Initial stubs exist (`gossipmesh/billing/`), but full Stripe integration and metered billing are planned for later milestones.

## 16. Observability
**Status:** Planned

Production observability is critical for monitoring the health of the SaaS platform. The implementation will include structured logging, distributed tracing (OpenTelemetry), and metrics collection to track system performance, API latency, and LLM provider availability.
