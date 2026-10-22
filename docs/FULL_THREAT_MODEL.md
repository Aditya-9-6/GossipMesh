# GossipMesh Enterprise SaaS Full Threat Model (Task 107)

This document establishes the comprehensive STRIDE threat model across all 12 architectural attack surfaces of GossipMesh Enterprise, mapping each threat to its concrete codebase mitigations and automated verification test suites.

---

## Threat Matrix & Mitigation Mapping

| Domain | Threat ID | STRIDE | Attack Description | Codebase Mitigation | Automated Test Coverage |
|---|---|---|---|---|---|
| **1. GitHub Integration** | `THREAT-GH-01` | Spoofing / Tampering | Forged webhook deliveries pretending to be GitHub events | Webhook HMAC-SHA256 verification via `verify_github_signature` | `tests/test_webhooks.py` |
| **2. Inbound Webhooks** | `THREAT-WH-02` | Repetition / Replay | Replaying captured webhook payloads to duplicate jobs or drain compute | Idempotency engine checking `IdempotencyRecord` table before dispatch | `tests/test_idempotency.py` |
| **3. Authentication** | `THREAT-AUTH-03` | Elevation of Privilege | Stolen JWT tokens used indefinitely | 15-minute access token lifespan, DB session revocation | `tests/test_auth_tokens.py` |
| **4. Multi-Tenant Boundaries** | `THREAT-TENANT-04` | Information Disclosure | SQL query tampering accessing another organization's repositories | Global ORM criteria injection via `SoftDeleteMixin` & `TenantMixin` | `tests/test_tenant_isolation.py` |
| **5. AI Providers & Keys** | `THREAT-AI-05` | Denial of Service | Quota exhaustion or 429 rate limit shutting down all reviews | `KeyPoolRouter` multi-key failover and 60-second cooldown circuit breaker | `tests/test_key_pool_router.py` |
| **6. RAG & Vector Retrieval** | `THREAT-RAG-06` | Information Disclosure | Vector search returning document chunks from a private unshared repo | Permission-aware retrieval filtering `DocumentChunk.organization_id` | `tests/test_permission_aware_retrieval.py` |
| **7. Prompt Injection** | `THREAT-PROMPT-07` | Tampering | Untrusted PR diff overriding review instructions via hidden markdown | `PromptPipeline` untrusted content XML boundary isolation & sanitization | `tests/test_prompt_pipeline.py` |
| **8. Execution Sandbox** | `THREAT-SBX-08` | Elevation of Privilege | Attacker executing fork bomb, path traversal, or reading host files | `RootlessContainerAdapter`, command whitelist, and `no-new-privileges` | `tests/test_sandbox_escapes.py` |
| **9. Billing & Metering** | `THREAT-BILL-09` | Tampering | Manipulation of metered usage quantities | Append-only immutable `UsageRecord` with unique `idempotency_key` | `tests/test_usage_metering.py` |
| **10. Support Break-Glass** | `THREAT-SUPP-10` | Elevation of Privilege | Rogue support engineer viewing customer proprietary source code | Dual-custody break-glass, explicit reason required, 4-hour max lease | `tests/test_support_breakglass.py` |
| **11. Artifacts & Quarantine** | `THREAT-ART-11` | Tampering | Malicious executable masked as a test artifact uploaded to server | `ArtifactQuarantineManager` SHA256 integrity check and malware quarantine | `tests/test_artifact_quarantine.py` |
| **12. Jobs & Worker Leases** | `THREAT-JOB-12` | Repetition | Split-brain workers concurrently modifying the same PR or repository | Monotonically increasing fencing tokens and heartbeat lease expiration | `tests/test_worker_leases.py` |

---

## 1. Domain Deep Dives

### GitHub & Webhook Authenticity
- Every webhook payload is rejected with HTTP 401 if `X-Hub-Signature-256` or `Stripe-Signature` fails cryptographic validation.
- Replayed deliveries are caught by the deduplication cache and return status `already_processed` without triggering duplicate worker tasks.

### Sandbox Escape Mitigations
- Commands are inspected through `CommandPolicyEngine` which enforces a deny-by-default whitelist.
- Subprocesses run inside rootless namespaces with restricted memory (`--memory=2g`), CPU quotas (`--cpus=1.0`), and dropped Linux capabilities (`cap_drop=["ALL"]`).
- Local filesystem access is restricted to an ephemeral scratch directory mounted at `/workspace`; symlink escapes outside the workspace boundary raise `SandboxSecurityError`.

### Prompt Injection Fencing
- All user-supplied PR titles, descriptions, and code diffs are encapsulated within `<untrusted_user_input>` XML tags.
- Review gates execute deterministically via static AST analyzers rather than relying solely on LLM self-evaluation.
