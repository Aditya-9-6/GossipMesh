"""Add repository_policies table (Task 37)

Revision ID: 7a1000000001
Revises: 524303fcc607
Create Date: 2026-10-21 18:35:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7a1000000001"
down_revision = "524303fcc607"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("branch_protection_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("auto_merge_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("require_review_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("min_approvals", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("allowed_target_branches", sa.JSON(), nullable=False),
        sa.Column("max_diff_lines", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("scan_frequency_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("custom_rules", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id"),
    )
    op.create_index(op.f("ix_repository_policies_id"), "repository_policies", ["id"], unique=False)
    op.create_index(op.f("ix_repository_policies_repository_id"), "repository_policies", ["repository_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_repository_policies_repository_id"), table_name="repository_policies")
    op.drop_index(op.f("ix_repository_policies_id"), table_name="repository_policies")
    op.drop_table("repository_policies")
