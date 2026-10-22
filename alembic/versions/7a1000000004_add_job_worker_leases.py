"""Add worker lease columns to jobs table (Task 63)

Revision ID: 7a1000000004
Revises: 7a1000000003
Create Date: 2026-10-21 18:55:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7a1000000004"
down_revision = "7a1000000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("worker_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("lease_token", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_index("ix_jobs_worker_id", ["worker_id"])
        batch_op.create_index("ix_jobs_lease_token", ["lease_token"])
        batch_op.create_index("ix_jobs_lease_expires_at", ["lease_expires_at"])


def downgrade() -> None:
    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_index("ix_jobs_lease_expires_at")
        batch_op.drop_index("ix_jobs_lease_token")
        batch_op.drop_index("ix_jobs_worker_id")
        batch_op.drop_column("attempts")
        batch_op.drop_column("heartbeat_at")
        batch_op.drop_column("lease_expires_at")
        batch_op.drop_column("lease_token")
        batch_op.drop_column("worker_id")
