# GossipMesh Status Page & Incident Communication Policy (Task 119)

This policy defines the service component statuses, incident severities, external communication SLAs, and blameless post-mortem standards for GossipMesh Enterprise.

---

## 1. Monitored Status Page Components (`status.gossipmesh.com`)

| Component Name | Description | Health Indicator Metric |
|---|---|---|
| **Core API** | REST API endpoints, auth, and billing | `gossipmesh_http_requests_total` success ratio >= 99.9% |
| **Webhook Ingestion** | GitHub & Stripe webhook processors | `gossipmesh_webhook_events_total` error rate < 0.1% |
| **AI Review Mesh** | Multi-agent code review pipeline | Worker lease heartbeat & execution latency |
| **Execution Sandbox** | Isolated rootless test runner | Sandbox failure rate < 1.0% |
| **Vector Search Engine** | pgvector code chunk retrieval | RAG query latency < 150ms |
| **Web Dashboard** | Customer SaaS frontend application | Liveness probe responsive |

---

## 2. Component Health States
- 🟢 **Operational:** All metrics healthy and within normal operating parameters.
- 🟡 **Degraded Performance:** Latency elevated or non-critical background jobs delayed, but core reviews functional.
- 🟠 **Partial Outage:** One subsystem degraded (e.g. secondary provider failover in effect).
- 🔴 **Major Outage:** Core API or PR review pipelines unavailable.
- 🔵 **Under Maintenance:** Scheduled maintenance window with advance notice.

---

## 3. Incident Severity & Communication SLAs

| Severity | Definition | Initial Notice SLA | Update Cadence | Post-Mortem SLA |
|---|---|---|---|---|
| **SEV-1 (Critical)** | Core review pipeline or API completely down for > 5% of users | `<= 15 minutes` | Every 30 minutes | 72 hours |
| **SEV-2 (High)** | Degradation in review latency or single-provider outage | `<= 30 minutes` | Every 1 hour | 5 business days |
| **SEV-3 (Moderate)** | Non-critical feature (e.g. audit export delayed, dashboard sluggish) | `<= 2 hours` | Every 4 hours | Upon request |
| **SEV-4 (Minor)** | Minor cosmetic or documentation issues | Next business day | Release notes | None |

---

## 4. Standard Customer Incident Templates

### 4.1 Investigating (Initial Post)
> **Title:** Investigating elevated review latency
> **Status:** Investigating
> **Message:** We are currently investigating an issue causing delays in autonomous pull request reviews. Our engineering team has been paged and is actively diagnosing root cause. New updates will be provided within 30 minutes.

### 4.2 Identified
> **Title:** Identified upstream provider rate limiting
> **Status:** Identified
> **Message:** We have identified elevated error rates with an upstream AI provider. Traffic has been rerouted to our secondary multi-provider failover pool. We are monitoring review queues as backlog drains.

### 4.3 Resolved
> **Title:** All systems operational
> **Status:** Resolved
> **Message:** The issue affecting pull request review latency has been fully resolved. All pending queues have processed cleanly and systems are operating normally. A formal post-mortem will follow.

---

## 5. Blameless Post-Mortem Template
Every SEV-1 and SEV-2 incident requires a formal blameless post-mortem published to customers within 72 hours, covering:
1. **Executive Summary:** Plain-language summary of what happened.
2. **Customer Impact:** Number of affected organizations, delayed PRs, duration.
3. **Root Cause Analysis (5 Whys):** Technical root cause without attributing blame.
4. **Timeline (UTC):** Minute-by-minute breakdown from detection to resolution.
5. **What Went Well / What Went Poorly:** Honest retrospection on tooling and alerting.
6. **Action Items:** P0/P1 engineering tickets to prevent recurrence with assigned owners and deadlines.
