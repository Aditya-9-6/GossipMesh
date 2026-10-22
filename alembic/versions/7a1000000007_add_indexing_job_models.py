"""Add index_jobs and file_index_records tables (Task 76)

Revision ID: 7a1000000007
Revises: 7a1000000006
Create Date: 2026-10-21 19:24:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7a1000000007"
down_revision = "7a1000000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "index_jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("branch", sa.String(length=256), nullable=False, server_default="main"),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("progress_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_indexed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunks_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("job_version", sa.String(length=32), nullable=False, server_default="v1"),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_index_jobs_organization_id", "index_jobs", ["organization_id"])
    op.create_index("ix_index_jobs_repository_id", "index_jobs", ["repository_id"])
    op.create_index("ix_index_jobs_status", "index_jobs", ["status"])

    op.create_table(
        "file_index_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("filepath", sa.String(length=1024), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column(
            "last_indexed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_file_index_records_organization_id", "file_index_records", ["organization_id"])
    op.create_index("ix_file_index_records_repository_id", "file_index_records", ["repository_id"])
    op.create_index("ix_file_index_records_filepath", "file_index_records", ["filepath"])
    op.create_index("ix_file_index_records_file_hash", "file_index_records", ["file_hash"])


def downgrade() -> None:
    op.drop_index("ix_file_index_records_file_hash", table_name="file_index_records")
    op.drop_index("ix_file_index_records_filepath", table_name="file_index_records")
    op.drop_index("ix_file_index_records_repository_id", table_name="file_index_records")
    op.drop_index("ix_file_index_records_organization_id", table_name="file_index_records")
    op.drop_table("file_index_records")

    op.drop_index("ix_index_jobs_status", table_name="index_jobs")
    op.drop_index("ix_index_jobs_repository_id", table_name="index_jobs")
    op.drop_index("ix_index_jobs_organization_id", table_name="index_jobs")
    op.drop_table("index_jobs")
