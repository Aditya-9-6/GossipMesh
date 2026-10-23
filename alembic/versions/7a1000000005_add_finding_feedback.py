"""Add finding_feedback table for human feedback learning (Task 74)

Revision ID: 7a1000000005
Revises: 7a1000000004
Create Date: 2026-10-21 19:15:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7a1000000005"
down_revision = "7a1000000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finding_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.String(length=128), nullable=False),
        sa.Column("repository_id", sa.String(length=128), nullable=False),
        sa.Column("finding_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("feedback_type", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column("user_comment", sa.Text(), nullable=True),
        sa.Column("corrected_severity", sa.String(length=32), nullable=True),
        sa.Column("corrected_category", sa.String(length=64), nullable=True),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("rule_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finding_feedback_organization_id", "finding_feedback", ["organization_id"])
    op.create_index("ix_finding_feedback_repository_id", "finding_feedback", ["repository_id"])
    op.create_index("ix_finding_feedback_finding_fingerprint", "finding_feedback", ["finding_fingerprint"])
    op.create_index("ix_finding_feedback_feedback_type", "finding_feedback", ["feedback_type"])


def downgrade() -> None:
    op.drop_index("ix_finding_feedback_feedback_type", table_name="finding_feedback")
    op.drop_index("ix_finding_feedback_finding_fingerprint", table_name="finding_feedback")
    op.drop_index("ix_finding_feedback_repository_id", table_name="finding_feedback")
    op.drop_index("ix_finding_feedback_organization_id", table_name="finding_feedback")
    op.drop_table("finding_feedback")
