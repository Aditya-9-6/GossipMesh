# GossipMesh Enterprise Release & Canary Deployment Process (Task 118)

This specification defines the formal release management process, semantic versioning policy, database migration safeguards, staging approval gates, canary rollouts, and rollback procedures for GossipMesh Enterprise.

---

## 1. Semantic Versioning & Changelog
- Releases adhere to **SemVer 2.0.0** (`MAJOR.MINOR.PATCH`):
  - **MAJOR:** Incompatible architectural changes or breaking API deprecations.
  - **MINOR:** Backward-compatible enterprise features (new scanners, billing plans, integrations).
  - **PATCH:** Backward-compatible bug fixes, security patches, and performance optimizations.
- Every release automatically compiles commit history into `CHANGELOG.md`.

---

## 2. Zero-Downtime Migration Policy (Expand / Contract)
- All database schema modifications must be backward-compatible with the currently running application code:
  1. **Phase 1 (Expand):** Add nullable columns, new tables, or non-blocking indexes (`CREATE INDEX CONCURRENTLY`).
  2. **Phase 2 (Deploy):** Deploy application version utilizing new columns with fallback reads.
  3. **Phase 3 (Backfill):** Backfill data asynchronously.
  4. **Phase 4 (Contract):** Remove legacy unused columns in a subsequent release.
- Destructive operations (`DROP COLUMN`, `DROP TABLE`, `ALTER TYPE`) are strictly prohibited in the same release as application code changes.

---

## 3. Staging Approval Gate & Automated Smoke Tests
Before any production deployment:
1. The release candidate image is deployed to the isolated Staging environment.
2. `python scripts/staging_smoke_test.py` executes against staging.
3. The Staging Approval Gate requires approval from a designated Release Engineer or Security Admin.

---

## 4. Canary Rollout Strategy

```
[Production Traffic]
        │
        ├──▶ (10% Traffic) ──▶ [Canary Pods (v0.2.0)] ──▶ [Error Rate < 0.1% for 30m] ──▶ Promote to 100%
        │                                                         │ (Spike > 0.1%)
        │                                                         ▼
        │                                               [Instant Rollback to v0.1.0]
        │
        └──▶ (90% Traffic) ──▶ [Baseline Pods (v0.1.0)]
```

- Canary pods run for a 30-minute observation window.
- Prometheus monitors `gossipmesh_http_errors_total` and latency histograms.
- If error rate exceeds 0.1%, automated canary rollback is triggered immediately.

---

## 5. Instant Rollback Procedure
```bash
# 1. Roll back Kubernetes deployment
kubectl rollout undo deployment/gossipmesh-api -n gossipmesh
kubectl rollout undo deployment/gossipmesh-worker -n gossipmesh

# 2. Revert canary routing
kubectl apply -f k8s/ingress.yaml

# 3. Verify health probes
curl -f http://app.gossipmesh.com/health/ready
```
