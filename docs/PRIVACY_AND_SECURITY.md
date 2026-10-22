# GossipMesh Privacy, Security & Data Flow Policy (Task 110)

This document describes the customer security architecture, data processing flows, approved subprocessors, retention schedules, and incident notification commitments for GossipMesh Enterprise.

---

## 1. Customer Security Architecture

### 1.1 Data Encryption
- **In Transit:** All external and intra-service communications enforce `TLS 1.3` (or `TLS 1.2` minimum) with modern cipher suites. Plaintext HTTP traffic is rejected at ingress.
- **At Rest:** Database volumes, backups, and artifact storage buckets enforce `AES-256-GCM` encryption via customer-managed or cloud KMS envelope keys.

### 1.2 Strict Multi-Tenant Isolation
- Tenant separation is enforced at the database layer via non-overridable ORM filters (`TenantMixin`).
- Code execution occurs inside isolated, non-root user container namespaces with dropped Linux capabilities and denied network egress.

---

## 2. Customer Data Flow & Storage

```
[Customer GitHub Org] 
         │ (Webhook over TLS)
         ▼
[GossipMesh Ingress] ──(HMAC Verified)──▶ [Ephemeral Execution Sandbox]
                                                     │
                                             (AST Extraction)
                                                     ▼
                                          [Vector Embedding (pgvector)]
                                                     │
                                              (Zero-Retention)
                                                     ▼
                                           [LLM Provider API]
                                                     │
                                            (Deterministic Gate)
                                                     ▼
                                          [Inline PR Comments]
```

- **Zero Permanent Source Storage:** GossipMesh processes pull request diffs ephemerally during active review execution. Raw source files are discarded upon workflow completion.
- **AST Embeddings:** Code chunks indexed for semantic context are strictly tenant-scoped and expire when repositories are disconnected.

---

## 3. Approved Subprocessors

GossipMesh contracts with industry-standard cloud providers adhering to SOC 2 Type II and ISO 27001 standards:

| Subprocessor | Purpose | Location | Data In Scope |
|---|---|---|---|
| **Amazon Web Services (AWS)** / **Google Cloud (GCP)** | Cloud infrastructure, database hosting, KMS | US & EU Regions | Encrypted database snapshots, vector storage |
| **Stripe, Inc.** | Payment card processing, subscription management | Global (PCI-DSS Level 1) | Billing contact email, subscription status (no card numbers stored by GossipMesh) |
| **Google Cloud Gemini Enterprise** | Upstream LLM inference | US & EU | Ephemeral prompt diffs (zero customer data training) |
| **OpenAI / Anthropic Enterprise** | Fallback LLM inference | US | Ephemeral prompt diffs (zero training retention) |

---

## 4. Retention and Deletion Schedules

- **Audit Logs:** Retained for 365 days by default for enterprise compliance.
- **Review Artifacts & Patches:** Retained for 30 days before automated purge.
- **Customer Deletion Request:** Soft-deleted immediately, hard-purged across all database tables, vector indexes, and object stores within 30 calendar days.

---

## 5. Security Incident Response & Breach Notification

- GossipMesh maintains a 24/7 on-call security response rotation.
- **Customer Notification SLA:** In the event of confirmed unauthorized access to customer data, GossipMesh will notify designated security administrators within **72 hours** of confirmation, detailing the scope, affected resources, and mitigation steps.
- **Certification Status Notice:** GossipMesh is designed in strict alignment with SOC 2 Type II trust principles and ISO 27001 requirements; formal third-party audit reports will be made available upon completion of the observation period.
