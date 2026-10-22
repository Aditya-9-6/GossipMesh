# GossipMesh Enterprise Operational Alerts and Incident Runbooks (Task 97)

This document establishes the operational alert thresholds, severity classifications, and step-by-step incident response runbooks for GossipMesh Enterprise SaaS.

---

## 1. Alert Threshold Matrix & Prometheus Rules

| Alert Name | Severity | Condition / Threshold | Window | Mitigation Summary |
|---|---|---|---|---|
| `APIErrorRateHigh` | SEV-1 | HTTP 5xx errors > 1% of total traffic | 5 min | Check upstream DB/provider; roll back recent deployment |
| `QueueBacklogSaturation` | SEV-2 | Queue depth > 500 pending jobs | 10 min | Autoscaling worker pool; check for stuck leases |
| `JobFailureSpike` | SEV-2 | Job failure rate > 5% of all executions | 15 min | Inspect dead-letter queue; triage failing agent steps |
| `ProviderOutageDetected` | SEV-1 | Upstream LLM provider 5xx/429 > 5 consecutive | 3 min | Trigger KeyPoolRouter fallback; rotate provider |
| `WebhookDeliveryFailure` | SEV-2 | GitHub/Stripe webhook delivery failure > 0.5% | 10 min | Verify webhook secrets, check signature header parsing |
| `DatabaseSaturation` | SEV-1 | Connection pool utilization > 85% or CPU > 90% | 5 min | Terminate runaway long transactions, scale connection pool |
| `SandboxSecurityViolation` | SEV-1 | Quarantine breach, egress violation, or escape attempt | Immediate | Freeze offending tenant sandbox; isolate runner host |
| `CostAnomalySpike` | SEV-2 | Hourly spend > 3x rolling 7-day average ($50+ floor) | 1 hour | Emergency cost controls shutdown; inspect token loops |
| `AuthZTenantViolation` | SEV-1 | Cross-tenant 403 access attempts > 5/min | 5 min | Block offending API key / token; audit access logs |

---

## 2. Incident Runbooks

### 2.1 Runbook: `APIErrorRateHigh` (SEV-1)
- **Symptoms:** User-facing 500/502 errors; alert firing in Grafana/PagerDuty.
- **Triage Steps:**
  1. Inspect structured JSON logs filtering by `level: "ERROR"` and `error_category`:
     ```bash
     grep '"level": "ERROR"' /var/log/gossipmesh/api.log | jq .error_category | sort | uniq -c
     ```
  2. Inspect trace spans via OpenTelemetry (`http.status_code >= 500`).
  3. Verify database liveness via `curl -s http://localhost:8000/health/database`.
- **Immediate Mitigation:**
  1. If caused by a bad release, execute instant canary rollback:
     ```bash
     kubectl rollout undo deployment/gossipmesh-api
     ```
  2. If caused by DB connection exhaustion, scale up connection pool or kill hung queries.

---

### 2.2 Runbook: `ProviderOutageDetected` (SEV-1)
- **Symptoms:** LLM calls returning 429 (Rate Limit) or 503 (Overloaded).
- **Triage Steps:**
  1. Check provider metrics: `gossipmesh_provider_failures_total`.
  2. Inspect `KeyPoolRouter` cooldown status in worker logs:
     ```bash
     grep "[KeyPoolRouter]" /var/log/gossipmesh/worker.log
     ```
- **Immediate Mitigation:**
  1. Activate multi-provider failover:
     - If Gemini is degraded, route to Claude/OpenAI pool via feature flag:
       ```bash
       python -m gossipmesh.cli switch-provider --fallback openai
       ```
  2. Add backup API keys to environment pool:
     ```bash
     export GEMINI_KEY_POOL="key1,key2,key3,key4,key5"
     ```

---

### 2.3 Runbook: `SandboxSecurityViolation` (SEV-1)
- **Symptoms:** Process isolation violation, unwhitelisted command execution, or path traversal detected by `CommandPolicyEngine` or `ArtifactQuarantineManager`.
- **Triage Steps:**
  1. Find offending job and tenant ID in structured logs:
     ```bash
     grep "SANDBOX_SECURITY_VIOLATION" /var/log/gossipmesh/worker.log | jq '{job_id, organization_id, message}'
     ```
  2. Inspect quarantined artifact status in `artifacts` table (`quarantine_status = "INFECTED"`).
- **Immediate Mitigation:**
  1. Suspend the offending tenant account immediately:
     ```bash
     python -m gossipmesh.cli tenant suspend --org-id <ORG_ID> --reason "Sandbox security violation"
     ```
  2. Terminate the isolated container/process namespace:
     ```bash
     podman rm -f <CONTAINER_ID>
     ```

---

### 2.4 Runbook: `CostAnomalySpike` (SEV-2)
- **Symptoms:** High token consumption velocity or runaway autonomous loops.
- **Triage Steps:**
  1. Run cost controls query:
     ```bash
     python -c "from gossipmesh.billing.cost_controls import CostControlsEngine; ..."
     ```
  2. Identify the top tenant consuming tokens:
     ```sql
     SELECT organization_id, sum(quantity) FROM usage_records WHERE metric_type = 'ai_tokens' AND recorded_at > NOW() - INTERVAL '1 hour' GROUP BY organization_id ORDER BY 2 DESC LIMIT 5;
     ```
- **Immediate Mitigation:**
  1. Trigger emergency budget shutdown for runaway organization:
     ```bash
     python -m gossipmesh.cli billing emergency-shutdown --org-id <ORG_ID>
     ```

---

### 2.5 Runbook: `DatabaseSaturation` (SEV-1)
- **Symptoms:** DB connection pool exhausted (`QueuePool limit of size 10 overflow 20 reached`).
- **Triage Steps:**
  1. Check PostgreSQL active connections:
     ```sql
     SELECT pid, age(clock_timestamp(), query_start), usename, query FROM pg_stat_activity WHERE state != 'idle' AND query NOT ILIKE '%pg_stat_activity%' ORDER BY query_start ASC;
     ```
- **Immediate Mitigation:**
  1. Terminate hung queries older than 5 minutes:
     ```sql
     SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE age(clock_timestamp(), query_start) > INTERVAL '5 minutes' AND state != 'idle';
     ```

---

### 2.6 Runbook: `AuthZTenantViolation` (SEV-1)
- **Symptoms:** Frequent 403 Forbidden spikes on resource access (`CrossTenantAccessViolation`).
- **Triage Steps:**
  1. Inspect `audit_events` table for unauthorized tenant boundaries:
     ```sql
     SELECT * FROM audit_events WHERE action LIKE '%unauthorized%' OR action LIKE '%violation%' ORDER BY timestamp DESC LIMIT 20;
     ```
- **Immediate Mitigation:**
  1. Invalidate compromised API keys or session tokens:
     ```sql
     UPDATE api_keys SET is_active = false WHERE id = <KEY_ID>;
     ```
