# GossipMesh 🌐

> **Decentralized P2P Gossip Protocol Multi-Agent Autonomous Engineering Mesh**  
> *A prototype AI engineering automation platform for autonomous coding agents.*

---

## 🌟 Overview

**GossipMesh** is currently a strong prototype for autonomous code-review agents, transitioning into a secure, multi-tenant AI agent SaaS platform. It aims to enable autonomous software engineering agents to cross-pollinate architectural wisdom, prevent repeated mistakes, enforce Byzantine quorum consensus, and maintain cross-repository wire compatibility.

---

## 🚀 Implemented Features

The following features have been implemented and integrated into the repository:
- **AST Parsing:** Extracts structural changes from Python and Go diffs to reduce LLM context bloat.
- **Gemini Embeddings & RAG:** Basic Retrieval-Augmented Generation using Gemini and local JSON vector search.
- **Semantic Caching:** Reduces redundant LLM API calls using vector embeddings via a local VectorDB.
- **AI PR Reviewer:** An autonomous loop that evaluates PRs and merges them if the score is $\ge 90/100$, or closes them if rejected.
- **AI CI Fixer & Issue Solver:** Scripts for AI issue implementation and CI repair.

## 🏗️ Prototype Features

These features currently exist as in-memory stubs, local scripts, or mock implementations, lacking a full database or API layer:
- **Local file-backed gossip node and ledger:** Peer nodes exchange cryptographically verified messages with vector clocks and TTL counters using local JSON files.
- **Memetic Knowledge Distillation (`gossipmesh.memetic`):** Persistent architectural knowledge and scoring using dynamic fitness scores.
- **Heterogeneous Multi-Model Byzantine Consensus (`gossipmesh.consensus`):** Multi-model vote aggregation (currently mocked for Gemini models).
- **Red Team vs. Blue Team Adversarial Auditing (`gossipmesh.red_team`):** Regex-based adversarial audit rules probing for vulnerabilities prior to PR creation.
- **Cross-Repo Wire Contract Synchronizer (`gossipmesh.bridge`):** Go/Rust wire-contract code generation.
- **Zero-Allocation Performance Regression Oracle (`gossipmesh.oracle`):** In-memory benchmark regression checks.
- **Contract Net Protocol Task Auction (`gossipmesh.auction`):** Keyword-based agent specialty selection for RFQs.

## 🔮 Planned Features

The platform is transitioning toward a full SaaS offering with the following planned features:
- **Multi-tenant Secure Platform:** Transitioning from local scripts to a provider-neutral agent platform.
- **Full Backend Stack:** Integration with FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic, Redis, and Celery for background workers.
- **Secure Agent Runtime:** A `SandboxEnvironment` for execution isolation, complete with `WorkflowManager`, `BudgetManager`, and robust database models.
- **Enterprise Controls & Billing:** Milestones for RBAC, provider credential encryption (Fernet), SaaS RAG, and scalable deployment.

### 5. Cross-Repo Wire Contract Synchronizer (`gossipmesh.bridge`)
- Translates shared data structures between **Go** ([`DevProxy`](https://github.com/GossipMesh/DevProxy)) and **Rust** ([`Spryzen`](https://github.com/GossipMesh/spryzen)).
- Generates matching Go structs and Rust Serde types automatically to prevent protocol divergence.
---

## ⚠️ Security Warnings

- **Do not use in production environments.** GossipMesh is a prototype.
- **Credential Security:** AI must never receive unrestricted production credentials. Do not provide sensitive values like database credentials or production API keys.
- **Execution Risks:** The framework currently executes AI-generated code. All patches must go through a validation pipeline. Do not push/merge without explicit policy authorization in non-development setups.

---

## 💻 Local Development Instructions

The project requires Python version >= 3.10. Dependencies are managed via `pyproject.toml`.

### Setup

```bash
# Clone the repository
git clone https://github.com/Aditya-9-6/GossipMesh.git
cd GossipMesh

# Create a virtual environment and activate it
python -m venv venv
source venv/bin/activate

# Install the package with API dependencies
pip install -e .[api]
```

### CLI Usage

```bash
# Check mesh status, active heartbeats, and top memetic knowledge
python -m gossipmesh.cli status

# Broadcast an architectural learning across all agent daemons
python -m gossipmesh.cli broadcast --topic anti_patterns --message "Use atomic buckets, avoid mutex on hot path" --repo DevProxy
```

### Testing

Run the comprehensive unit test suite:

```bash
# Setup development environment variables to bypass strict signature verification if needed
export ENVIRONMENT="development"

# Run tests
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 🚦 Production Deployment Status

**Not ready for production.** GossipMesh is currently in a prototype phase and lacks the full realization and dependencies for its planned SaaS stack. It is intended strictly for local development and conceptual validation.

For more details on our path to production and architectural decisions, please refer to the following documentation:
- [Production Readiness](docs/PRODUCTION_READINESS.md)
- [Architecture](docs/ARCHITECTURE.md)

---

## 📜 License

Apache-2.0 License. Built by [Maintainers](https://github.com/Maintainers).
