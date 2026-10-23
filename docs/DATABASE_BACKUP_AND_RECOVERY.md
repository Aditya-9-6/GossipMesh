# GossipMesh Database Backup, Restore, and Disaster Recovery Runbook (Task 32)

This document specifies the PostgreSQL backup, Point-in-Time Recovery (PITR), encryption, and tenant data export procedures for GossipMesh Enterprise SaaS.

---

## 1. Objectives & SLAs

| Metric | Target | Description |
| :--- | :--- | :--- |
| **RPO (Recovery Point Objective)** | **$\le$ 5 minutes** | Maximum allowable data loss in the event of hardware or cluster failure. |
| **RTO (Recovery Time Objective)** | **$\le$ 30 minutes** | Maximum duration required to provision standby nodes and restore service. |
| **Retention Policy** | **30 days** | Daily encrypted snapshots retained for 30 days in air-gapped immutable storage. |

---

## 2. Backup Architecture

GossipMesh employs a two-tier backup strategy:
1. **Continuous Write-Ahead Logging (WAL):** WAL segments are streamed continuously to object storage using `pgBackRest` / `WAL-G`.
2. **Encrypted Daily Snapshots:** Automated daily full dumps encrypted at rest with AES-256 via `gossipmesh.db.backup.DatabaseBackupManager`.

```
[PostgreSQL Primary]
       │
       ├── Continuous WAL Stream ──────> [S3/GCS Immutable Bucket]
       └── Daily Encrypted Snapshot ───> [Cold Glacier/Vault Storage]
```

---

## 3. Automated Backup & Encryption Procedure

Snapshots are encrypted using AES-256-GCM / Fernet derived from the organization's `ENCRYPTION_KEY`.

### Command Line Invocation
```bash
# Generate full encrypted snapshot with SHA-256 verification
python -c "
from gossipmesh.db.backup import DatabaseBackupManager
mgr = DatabaseBackupManager(backup_dir='./backups')
path, meta = mgr.create_snapshot(db_name='gossipmesh')
print(f'Created backup: {path} (SHA-256: {meta.checksum_sha256})')
"
```

---

## 4. Point-in-Time Recovery (PITR) Runbook

In the event of accidental data corruption or logical deletion:

1. **Stop Application Workloads:**
   ```bash
   kubectl scale deployment gossipmesh-api --replicas=0
   kubectl scale deployment gossipmesh-worker --replicas=0
   ```

2. **Restore Base Snapshot:**
   ```bash
   pg_restore -C -d postgres ./backups/base_snapshot.dump
   ```

3. **Configure Recovery Target in `postgresql.conf`:**
   ```ini
   restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
   recovery_target_time = '2026-10-21 17:30:00 UTC'
   recovery_target_action = 'promote'
   ```

4. **Start PostgreSQL in Recovery Mode:**
   ```bash
   systemctl start postgresql
   ```
   PostgreSQL plays WAL segments up to the exact target second and promotes itself to read-write.

5. **Verify Row Counts & Table Integrity:**
   ```bash
   python -m unittest tests/test_backup_restore.py
   ```

6. **Resume Workloads:**
   ```bash
   kubectl scale deployment gossipmesh-api --replicas=3
   kubectl scale deployment gossipmesh-worker --replicas=5
   ```

---

## 5. Tenant-Scoped Data Export (GDPR Portability)

To extract all data belonging exclusively to a single tenant:

```python
from gossipmesh.db.backup import DatabaseBackupManager
from gossipmesh.db.session import SessionLocal

session = SessionLocal()
mgr = DatabaseBackupManager()
export_data = mgr.export_tenant_data(session, organization_id=42, output_file="exports/tenant_42.json")
```

The exported file contains the tenant's organization record, users, repositories, runs, and budgets, with all cross-tenant access cryptographically isolated.
