"""Expand artifact table for quarantine and malware scanning (Task 84)

Revision ID: 7a1000000008
Revises: 7a1000000007
Create Date: 2026-10-21 19:42:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7a1000000008"
down_revision = "7a1000000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("artifacts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(
            sa.Column("content_type", sa.String(), nullable=False, server_default="application/octet-stream")
        )
        batch_op.add_column(sa.Column("sha256_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("quarantine_status", sa.String(length=32), nullable=False, server_default="QUARANTINED")
        )
        batch_op.add_column(sa.Column("scan_results", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("retention_days", sa.Integer(), nullable=False, server_default="30"))
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"))

        batch_op.create_index("ix_artifacts_organization_id", ["organization_id"])
        batch_op.create_index("ix_artifacts_quarantine_status", ["quarantine_status"])
        batch_op.create_index("ix_artifacts_sha256_hash", ["sha256_hash"])


def downgrade() -> None:
    with op.batch_alter_table("artifacts", schema=None) as batch_op:
        batch_op.drop_index("ix_artifacts_sha256_hash")
        batch_op.drop_index("ix_artifacts_quarantine_status")
        batch_op.drop_index("ix_artifacts_organization_id")

        batch_op.drop_column("download_count")
        batch_op.drop_column("expires_at")
        batch_op.drop_column("retention_days")
        batch_op.drop_column("scan_results")
        batch_op.drop_column("quarantine_status")
        batch_op.drop_column("sha256_hash")
        batch_op.drop_column("content_type")
        batch_op.drop_column("size_bytes")
        batch_op.drop_column("organization_id")
